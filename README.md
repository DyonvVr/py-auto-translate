# py-auto-translate
The aim of this Python script is to provide an automatic multilingual translation of text bodies for language learning purposes.

Besides bare translation, it offers a mode for word-by-word translation accompanying the text translation, for easy lookup and better understanding of new words. This was inspired by Ilya Frank's reading method, about which you can read more [here](http://english.franklang.ru/index.php?option=com_content&view=article&id=1&Itemid=11).

It offers support for the Google and Bing web page translators, as well as the Google Cloud Translate API*.

Furthermore, Auto translate can build LaTeX files for the creation of nicely formatted PDF documents containing the translation, using the [polyglossia](https://ctan.org/pkg/polyglossia) package for multilingual typesetting. These files must be compiled with XeLaTeX or LuaLaTeX.

## Installation
Make sure you have Python 3 installed.
Furthermore install the following dependencies (for example via the `pip install` command):
- `googletrans==3.1.0a0`
- `translators>=4.7.10`
- `google.cloud`
- `google-cloud-translate`
- `ntpath`
- `numpy`
- `pandas`
- `numpy`
- `re`

In order to use Google Cloud Translate API translation, you must set up a Google Cloud project with Translate API enabled.

## Usage
Place a text file in the directory where `auto_translate.py` is located, and run the following command in the terminal:
```
python auto_translate.py <text file>
```
This produes an output (either as a text or LaTeX file) in the output directory (specified in the `config` file).

## Skipping words in word-by-word translation
When generating word-by-word translations, it may be useful to skip certain words in order to prevent bloating the word-by-word translation with words that are already known to the reader.
Auto translate has a feature built in to skip words specified in a word skip list.

To use this feature, enabled word skipping in the configuration file and provide a text file named `<language code>.txt` in the directory `./word_skip_lists`, where `<language code>` is the language code of the (detected) source language used by the translation provider.
This word skip list must contain each word on a *separate line*. Instead of words, you can also use regular expressions.

The repository contains an example word skip list for English.

## Configuration
The `config.txt` file lists several options which can be set to one own's preferences.

### Notes
*User is responsible for the costs of using Google Cloud services.
