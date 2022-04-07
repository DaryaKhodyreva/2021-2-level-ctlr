"""
Scrapper implementation
"""

import json
import re
import shutil
import pathlib
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from constants import ASSETS_PATH, CRAWLER_CONFIG_PATH, HTTP_PATTERN
from core_utils.article import Article


class IncorrectURLError(Exception):
    """
    Seed URL does not match standard pattern
    """


class NumberOfArticlesOutOfRangeError(Exception):
    """
    Total number of articles to parse is too big
    """


class IncorrectNumberOfArticlesError(Exception):
    """
    Total number of articles to parse in not integer
    """


class Crawler:
    """
    Crawler implementation
    """
    def __init__(self, seed_urls, max_articles: int):
        self.max_articles = max_articles
        self.seed_urls = seed_urls
        self.urls = []

    def _extract_url(self, article_bs):
        urls_bs = article_bs.find_all('a', class_="item__link")
        all_urls = []

        for url_bs in urls_bs:
            last_part = url_bs['href']
            all_urls.append(f'{HTTP_PATTERN}{last_part}')
        return all_urls

    def find_articles(self):
        """
        Finds articles
        """
        for seed_url in self.seed_urls:
            response = requests.get(url=seed_url)

            soup_lib = BeautifulSoup(response.text, 'lxml')

            urls = self._extract_url(soup_lib)
            for url in urls:
                if len(self.urls) < self.max_articles:
                    if url not in self.urls:
                        self.urls.append(url)

    def get_search_urls(self):
        """
        Returns seed_urls param
        """
        return self.seed_urls


class HTMLParser:
    def __init__(self, article_url, article_id):
        self.article_url = article_url
        self.article_id = article_id
        self.article = Article(article_url, article_id)

    def _fill_article_with_meta_information(self, article_bs):
        title_parent = article_bs.find('div', class_='article__header__title')
        title = title_parent.find('h1', class_='article__header__title-in js-slide-title').text  # print the title
        self.article.title = title.strip()   # delete spaces

        author_parent = article_bs.find('a', class_='article__authors__author')
        if author_parent in article_bs:
            author = author_parent.find('span', class_='article__authors__author__name')
            self.article.author = author.text
        else:
            self.article.author = 'NOT FOUND'

        self.article.date = 'NOT FOUND'
        self.article.topics = 'NOT FOUND'

    def _fill_article_with_text(self, article_bs):
        self.article.text = ''
        block_1 = article_bs.find('div', class_='article__text article__text_free')
        txt_group1 = block_1.find_all('p')
        txt_group1 = txt_group1.select_one('a').decompose()
        for i in txt_group1:
            self.article.text += i.text

        block_2 = article_bs.find('div', class_='article__text')
        txt_group2 = block_2.find_all('p')
        txt_group2 = txt_group2.select_one('a').decompose()  # delete irrelevant tag
        for k in txt_group2:
            self.article.text += k.text

    def parse(self):
        response = requests.get(self.article_url)
        article_bs = BeautifulSoup(response.text, 'lxml')

        self._fill_article_with_text(article_bs)
        self._fill_article_with_meta_information(article_bs)

        return self.article


def prepare_environment(base_path):
    """
    Creates ASSETS_PATH folder if not created and removes existing folder
    """
    path = pathlib.Path(base_path)

    if path.exists():
        shutil.rmtree(base_path)
    path.mkdir(parents=True, exist_ok=True)


def validate_config(crawler_path):
    """
    Validates given config
    """
    with open(crawler_path) as file:
        config = json.load(file)

    seed_urls = config['seed_urls']
    total_articles = config['total_articles_to_find_and_parse']

    if not seed_urls:
        raise IncorrectURLError
    for article_url in seed_urls:
        correct_url = re.match(r'https://', article_url)
        if not correct_url:
            raise IncorrectURLError

    if not isinstance(total_articles, int):
        raise IncorrectNumberOfArticlesError

    if total_articles <= 0:
        raise IncorrectNumberOfArticlesError

    if total_articles > 200:
        raise NumberOfArticlesOutOfRangeError

    return seed_urls, total_articles


if __name__ == '__main__':
    seed_links, mx_articles = validate_config(CRAWLER_CONFIG_PATH)
    prepare_environment(ASSETS_PATH)
    crawler = Crawler(seed_urls=seed_links, max_articles=mx_articles)
    crawler.find_articles()

    COUNTER = 0
    for a_text in crawler.urls:
        COUNTER += 1
        parser = HTMLParser(a_text, COUNTER)
        article = parser.parse()
        article.save_raw()
