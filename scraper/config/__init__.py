import json
import os
import pathlib

_HERE = pathlib.Path(__file__).resolve().parent


def load_config(name):
    with open(os.path.join(_HERE, name), "r", encoding="utf-8") as f:
        return json.load(f)


company_config = load_config("company.json")
scraper_config = load_config("scraper.json")
