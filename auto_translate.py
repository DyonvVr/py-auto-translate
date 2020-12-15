import ntpath
import numpy as np
import pandas as pd
import os
import re
import sys
import time
import translators as ts
from datetime import datetime
from googletrans import Translator
from google.cloud import translate_v2 as translate_gcp

class TranslatorWriter:
	def __init__(self, config):
		self.config = config
		self.lang_support = pd.read_csv("lang_support.csv", sep=";", index_col=0)
		self.translator_google = Translator()
		self.translator_gcp = None
		self.word_skip_list = None
		
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
			source_lang_translator = (None if source_lang=="auto" else source_lang)
			translation = self.translator_gcp.translate\
			(
				source,
				source_language=source_lang_translator,
				target_language=target_lang
			)
			target = translation["translatedText"]
			if source_lang == "auto": # changed to detected language code after detection
				source_lang_detected = translation["detectedSourceLanguage"]
		elif self.config["translator_provider"] == "bing":
			translation = ts.bing(source, from_language=source_lang,
								  to_language=target_lang, is_detail_result=True)
			target = translation[0]["translations"][0]["text"]
			source_lang_detected = translation[0]["detectedLanguage"]["language"]
		
		return {"target": target, "source_lang_detected": source_lang_detected, "char_count": len(source)}
	
	def is_in_skip_list(self, word):
		if self.word_skip_list == None:
			return False
		for regex in self.word_skip_list:
			if re.fullmatch(regex, word):
				return True
		return False
	
	def translate_write(self, source_file_name):
		translated_chars = 0
		
		source_file = open(source_file_name, "r", encoding="utf-8")
		source = " ".join(source_file.read().splitlines())
		source_file.close()
		
		source_split = re.split(r"([\.\?!…]+ )", source)
		source_sentences = ["".join([s, t]) for s, t in zip(source_split[::2], source_split[1::2] + [""])]
		
		source_lang = self.config["source_lang"]
		if self.config["source_lang"] == "auto": # translate first sentence to detect source language
			first_sentence_translation = self.translate(source_sentences[0], source_lang)
			source_lang = first_sentence_translation["source_lang_detected"]
			translated_chars += first_sentence_translation["char_count"]
			print("Detected source language: \"{}\"".format(source_lang))
		
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
		
		if self.config["skip_words"] == "true":
			if self.config["learning_method"] == "true":
				try:
					word_skip_list_file = open("./word_skip_lists/{}.txt".format(source_lang),
											   "r", encoding="utf-8")
					word_skip_list = [line.replace("\n", "") for line in word_skip_list_file.readlines()]
				except FileNotFoundError:
					print("Warning: no word skip list was found for source language \"{}\".\
						  No words will be skipped in the word-by-word translation.".format(source_lang))
			else:
				print("Warning: skip_words was enabled while learning_method was disabled.\
					  Words are only skipped in the word-by-word translation generated when\
					  learning_method is enabled.")
		
		for source_sentence in source_sentences:
			sentence_translation = self.translate(source_sentence, source_lang)
			target_sentence = sentence_translation["target"]
			translated_chars += sentence_translation["char_count"]
			
			word_by_word_translation = []
			for source_word in source_sentence.lower().split():
				source_word_clean = re.sub(r"[\W+]", "", source_word)
				if self.is_in_skip_list(source_word_clean): continue
				word_translation = self.translate(source_word_clean, source_lang)
				target_word = word_translation["target"]
				translated_chars += word_translation["char_count"]
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
					source_lang,
					self.config["target_lang"],
					ntpath.basename(source_file_name).partition(".")[0],
					source_lang,
					self.config["target_lang"]
				)
				os.makedirs(os.path.dirname(target_file_name), exist_ok=True)
			else:
				target_file_name = "{}_translated_{}_{}.tex".format\
				(
					ntpath.basename(source_file_name).partition(".")[0],
					source_lang,
					self.config["target_lang"]
				)
		
		output_dir = self.config["output_dir"].replace("\\", "/")
		if output_dir[-1] not in ["/", "\\"]:
			output_dir += "/"
		
		target_file = open(output_dir + target_file_name, "w", encoding="utf-8")
		target_file.write(target)
		target_file.close()
		
		print()
		
		if self.config["track_translated_chars"] == "true":
			print("{} characters translated".format(translated_chars))
		char_log_file = open("translated_chars.log", "a", encoding="utf-8")
		char_log_file.write("[{}]\t{}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), translated_chars))
		char_log_file.close()
		
		print("Translation written to {}".format(output_dir + target_file_name))

def check_config_option(config, key, option):
	if key == "output_dir":
		return 0 # valid path must be checked elsewhere
	elif key == "translator_provider":
		possible_options = ["google", "google_cloud", "bing"] + [""]
	elif key == "source_lang":
		return 0 # language support is checked in TranslatorWriter class
	elif key == "target_lang":
		return 0 # language support is checked in TranslatorWriter class
	elif key == "verbose":
		possible_options = ["true", "false"] + [""]
	elif key == "write_mode":
		possible_options = ["txt", "tex"] + [""]
	elif key == "tex_build_dir":
		possible_options = ["true", "false"] + [""]
	elif key == "learning_method":
		possible_options = ["true", "false"] + [""]
	elif key == "skip_words":
		possible_options = ["true", "false"] + [""]
	elif key == "track_translated_chars":
		possible_options = ["true", "false"] + [""]
	else:
		return 1 # invalid key
	
	if option in possible_options:
		return 0 # valid key and option
	else:
		return 2 # valid key, invalid option

def load_config():
	config =\
	{
		"output_dir": "",
		"translator_provider": "",
		"source_lang": "",
		"target_lang": "",
		"verbose": "",
		"write_mode": "",
		"tex_build_dir": "",
		"learning_method": "",
		"skip_words": "",
		"track_translated_chars": ""
	}
	
	config_file = open("config.txt", "r", encoding="utf-8")
	
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
		
		check_config_option_exit_code = check_config_option(config, key, option)
		if check_config_option_exit_code == 1:
			raise ValueError("key \"{}\" unknown in config line {}: \"{}\"".format(key, line_count, line))
		elif check_config_option_exit_code == 2:
			raise ValueError("option \"{}\" unknown for key \"{}\" in config line {}: \"{}\"".format(option, key, line_count, line))
		config[key] = option
		
	# default options
	if config["output_dir"] == "":
		config["output_dir"] = "./"
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
	if config["skip_words"] == "":
		config["skip_words"] = "false"
	if config["track_translated_chars"] == "":
		config["track_translated_chars"] = "false"
	
	config_file.close()
	
	print(config)
	
	return config

def main(argv):
	lang_support = pd.read_csv("lang_support.csv", sep=";", index_col=0)
	config = load_config()	
	tw = TranslatorWriter(config)
	tw.translate_write(argv[0])

if __name__ == "__main__":
	main(sys.argv[1:])