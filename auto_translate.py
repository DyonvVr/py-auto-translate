import ntpath
import numpy as np
import pandas as pd
import os
import re
import sys
import translators as ts
from googletrans import Translator
from google.cloud import translate_v2 as translate_gcp

class TranslatorWriter:
	def __init__(self, config):
		self.config = config
		self.lang_support = pd.read_csv("lang_support.csv", sep=";", index_col=0)
		self.translator_google = Translator()
		self.translator_gcp = None
		if self.config["translator_provider"] == "google_cloud":
			self.translator_gcp = translate_gcp.Client()
	
	def check_lang_support(self, lang, translator_provider):
		direction = ""
		
		if lang == self.config["source_lang"]:
			direction = "source"
		elif lang == self.config["target_lang"]:
			direction = "target"
		
		if not lang in self.lang_support.index:
			raise ValueError("{} language \"{}\" is not supported".format(direction, lang))
		
		if self.lang_support[translator_provider][lang] is np.nan:
			raise ValueError("{} language \"{}\" is not supported by translator provider \"{}\"".format(direction, lang, translator_provider))
		
		if self.config["write_mode"] == "tex":
			if self.lang_support["polyglossia"][lang] is np.nan:
				print("Warning: {} language \"{}\" is not supported by polyglossia. When using LaTeX, hyphenation may be incorrect or missing.".format(direction, lang))
			
	def translate(self, source, source_lang):
		target_lang = self.config["target_lang"]
		target = ""
		source_lang_detected = ""
		
		if self.config["translator_provider"] == "google":
			translation = self.translator_google.translate(source, src=source_lang, dest=target_lang)
			target = translation.text
			source_lang_detected = translation.src
		elif self.config["translator_provider"] == "google_cloud":
			translation = translator_gcp.translate(source, source_language=source_lang, target_language=target_lang)
			target = translation["translatedText"]
			source_lang_detected = translation["detectedSourceLanguage"]
		elif self.config["translator_provider"] == "bing":
			translation = ts.bing(source, from_language=source_lang,
								  to_language=target_lang, is_detail_result=True)
			target = translation[0]["translations"][0]["text"]
			source_lang_detected = translation[0]["detectedLanguage"]["language"]
		
		return {"target": target, "source_lang_detected": source_lang_detected}
	
	def translate_write(self, source_file_name):				
		source_file = open(source_file_name, "r", encoding="utf-8")
		source = " ".join(source_file.read().splitlines())
		source_file.close()
		
		source_split = re.split(r"([\.\?!…]+ )", source)
		source_sentences = ["".join([s, t]) for s, t in zip(source_split[::2], source_split[1::2] + [""])]
		
		source_lang = self.config["source_lang"]
		if self.config["source_lang"] == "auto":
			source_lang = self.translate(source_sentences[0], source_lang)["source_lang_detected"]
		
		self.check_lang_support(source_lang, self.config["translator_provider"])
		target_lang = self.config["target_lang"]
		self.check_lang_support(target_lang, self.config["translator_provider"])
		
		target = ""
		
		if self.config["write_mode"] == "tex":
			if self.config["tex_build_dir"] == "true":
				target += "\\input{../preamble.tex}\n\n"
			else:
				target += "\\input{preamble.tex}\n\n"
			
			polyg_sup_src = self.lang_support["polyglossia"][source_lang]
			polyg_sup_trg = self.lang_support["polyglossia"][target_lang]
			
			if polyg_sup_src is not np.nan:
				target += "\\setmainlanguage{{{}}}\n\n".format(polyg_sup_src)
			if polyg_sup_trg is not np.nan:
				target = target[:-1]
				if polyg_sup_src is not np.nan:
					target += "\\setotherlanguage{{{}}}\n\n".format(polyg_sup_trg)
				else:
					target +=  "\\setmainlanguage{{{}}}\n\n".format(polyg_sup_trg)
			
			target += "\\begin{document}\n\n"
			
			if polyg_sup_src is not np.nan:
				target += "\\begin{{{}}}\n".format(polyg_sup_src)
			target += source + "\n\n"
			if polyg_sup_src is not np.nan:
				target = target[:-1] # remove last newline
				target += "\\end{{{}}}\n\n".format(polyg_sup_src)
			
			if self.config["learning_method"] == "false":
				if polyg_sup_trg is not np.nan:
					target += "\\begin{{{}}}\n".format(polyg_sup_trg)
		
		for source_sentence in source_sentences:		
			target_sentence = self.translate(source_sentence, source_lang)["target"]
			
			word_by_word_translation = []
			for source_word in source_sentence[:-1].lower().split():
				source_word_clean = re.sub("[\W+]", "", source_word)
				target_word = self.translate(source_word_clean, source_lang)["target"]
				word_by_word_translation.append([source_word, target_word])
			
			if self.config["write_mode"] == "txt":
				if self.config["learning_method"] == "true":
					target += source_sentence + "\n"
				target += target_sentence + "\n"
				if self.config["learning_method"] == "true":
					for entry in word_by_word_translation:
						target += "{} = {}; ".format(entry[0], entry[1])
					target = target[:-2] # truncate last separator + space
					target += "\n\n"
				
			elif self.config["write_mode"] == "tex":
				if self.config["learning_method"] == "true":
					target += "{\\bf " + source_sentence + "}\\\\\n"
				target += target_sentence + "\n"
				if self.config["learning_method"] == "true":
					target = target[:-1] + "\\\\\n" # remove last \n, replace by \\\\\n
					target += "{\\color{darkgreen} "
					for entry in word_by_word_translation:
						target += "{} = {}; ".format(entry[0], entry[1])
					target = target[:-2] # truncate last separator + space
					target += "}\n\n"
			
			if self.config["verbose"] == "true":
				print("[source] {}".format(source_sentence))
				print("[target] {}".format(target_sentence))
				sys.stdout.flush()
		
		if self.config["write_mode"] == "tex":
			if self.config["learning_method"] == "false":
				if polyg_sup_trg is not np.nan:
					target += "\\end{{{}}}\n".format(polyg_sup_trg)	
				target += "\n"
			target += "\\end{document}"
		
		target_file_name = ""
		
		if self.config["write_mode"] == "txt":
			target_file_name = "{}_translated_{}_{}.txt".format\
			(
				ntpath.basename(source_file_name).partition(".")[0],
				self.config["source_lang"],
				self.config["target_lang"]
			)
		elif self.config["write_mode"] == "tex":
			if self.config["tex_build_dir"] == "true":
				target_file_name = "{}_translated_{}_{}/{}_translated_{}_{}.tex".format\
				(
					ntpath.basename(source_file_name).partition(".")[0],
					self.config["source_lang"],
					self.config["target_lang"],
					ntpath.basename(source_file_name).partition(".")[0],
					self.config["source_lang"],
					self.config["target_lang"]
				)
				os.makedirs(os.path.dirname(target_file_name), exist_ok=True)
			else:
				target_file_name = "{}_translated_{}_{}.tex".format\
				(
					ntpath.basename(source_file_name).partition(".")[0],
					self.config["source_lang"],
					self.config["target_lang"]
				)
			
		target_file = open(target_file_name, "w", encoding="utf-8")
		target_file.write(target)
		target_file.close()
		
		print("Translation written to ./{}".format(target_file_name))

def load_config():
	config =\
	{
		"translator_provider": "",
		"source_lang": "",
		"target_lang": "",
		"verbose": "",
		"write_mode": "",
		"tex_build_dir": "",
		"learning_method": "",
	}
	
	config_file = open("config", "r")
	
	line_count = 0
	
	for line in config_file:
		line_count += 1
		
		line_no_whitespace = "".join(line.split())
		if line_no_whitespace == "" or line_no_whitespace[0] == "#": continue
		
		partition = line_no_whitespace.partition("=")
		
		if partition[1] != "=":
			raise ValueError("syntax error in line {}: \"{}\"".format(line_count, line))
		
		key = partition[0].strip()
		option = partition[2].strip()
		
		if key == "translator_provider":
			if option in ["google", "google_cloud", "bing"] + [""]:
				config["translator_provider"] = option
			else:
				raise ValueError("option \"{}\" unknown for key \"{}\" in config line {}: \"{}\"".format(option, key, line_count, line))
		elif key == "source_lang":
			pass # language support is checked in TranslatorWriter class
		elif key == "target_lang":
			pass # language support is checked in TranslatorWriter class
		elif key == "verbose":
			if option in ["true", "false"] + [""]:
				config["verbose"] = option
			else:
				raise ValueError("option \"{}\" unknown for key \"{}\" in config line {}: \"{}\"".format(option, key, line_count, line))
		elif key == "write_mode":
			if option in ["txt", "tex"] + [""]:
				config["write_mode"] = option
			else:
				raise ValueError("option \"{}\" unknown for key \"{}\" in config line {}: \"{}\"".format(option, key, line_count, line))
		elif key == "tex_build_dir":
			if option in ["true", "false"] + [""]:
				config["tex_build_dir"] = option
			else:
				raise ValueError("option \"{}\" unknown for key \"{}\" in config line {}: \"{}\"".format(option, key, line_count, line))
		elif key == "learning_method":
			if option in ["true", "false"] + [""]:
				config["learning_method"] = option
			else:
				raise ValueError("option \"{}\" unknown for key \"{}\" in config line {}: \"{}\"".format(option, key, line_count, line))
		else:
			raise ValueError("key \"{}\" unknown in line {}: \"{}\"".format(key, line_count, line))
		
	# default options
	if config["translator_provider"] == "":
		config["translator_provider"] = "google"
	if config["source_lang"] == "":
		config["source_lang"] = "auto"
	if config["target_lang"] == "":
		config["target_lang"] = "en"
	if config["verbose"] == "":
		config["verbose"] = "false"
	if config["write_mode"] == "":
		config["write_mode"] = "txt"
	if config["tex_build_dir"] == "":
		config["tex_build_dir"] = "false"
	if config["learning_method"] == "":
		config["learning_method"] = "false"
	
	config_file.close()
	
	return config

def main(argv):
	lang_support = pd.read_csv("lang_support.csv", sep=";", index_col=0)
	config = load_config()	
	tw = TranslatorWriter(config)
	tw.translate_write(argv[0])

if __name__ == "__main__":
	main(sys.argv[1:])