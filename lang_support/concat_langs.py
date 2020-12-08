import pandas as pd

def main():
	google      = pd.read_csv("google.csv",      sep=";", index_col=0)
	bing        = pd.read_csv("bing.csv",        sep=";", index_col=0)
	yandex      = pd.read_csv("yandex.csv",      sep=";", index_col=0)
	polyglossia = pd.read_csv("polyglossia.csv", sep=";", index_col=0)
	
	langs = [google, bing, yandex, polyglossia]
	lang_support = pd.concat(langs, axis=1, sort=True)
	lang_support.to_csv("lang_support.csv", sep=";")

if __name__ == "__main__":
	main()