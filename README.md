# py-auto-translate
The aim of this Python script is to provide an automatic multilingual translation of text bodies of language learning purposes.
Besides bare translation, it offers a mode for word-by-word translation accompanying the text translation, for easy lookup and better understanding of new words. This was inspired by Ilya Frank's reading method, about which you can read more [here](http://english.franklang.ru/index.php?option=com_content&view=article&id=1&Itemid=11).
Auto translate offers support for Google and Bing translators.
Furthermore, Auto translate can build LaTeX files for the creation of nicely formatted PDF files containing the translation, using the [polyglossia](https://ctan.org/pkg/polyglossia) package for multilingual typesetting. These files must be compiled with XeLaTeX or LuaLaTeX.

# Installation
Make sure you have Python 3 installed.
Furthermore install the following dependencies (for example via the `pip install` command):
- `googletrans==3.1.0a0`
- `translators>=4.7.10`
- `ntpath`
- `numpy`
- `pandas`
- `numpy`
- `re`

# Usage
Place a text file in the directory where `auto_translate.py` is located, and run the following command in the terminal:
```
python auto_translate.py <text file>
```
This produes an output (either as a text or LaTeX file) in the same directory.

# Configuration
The `config` file lists several options for Auto translate (such as which translation provider to use) which can be set to one own's preferences.

# To do
- Yandex translation support
- Better handling of input/output directories
