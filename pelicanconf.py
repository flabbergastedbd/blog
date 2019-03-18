#!/usr/bin/env python
# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Bharadwaj Machiraju'
SITENAME = 'bharadwaj.machiraju'
SITEURL = 'https://tunnelshade.in'

PATH = 'content'

TIMEZONE = 'Asia/Kolkata'
DEFAULT_DATE_FORMAT = "%d-%m-%y"

DEFAULT_LANG = 'en'

# Feed generation is usually not desired when developing
FEED_ALL_ATOM = 'feeds/all.atom.xml'
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

# Blogroll
LINKS = (('Pelican', 'http://getpelican.com/'),
         ('You can modify those links in your config file', '#'),)

# Social widget
SOCIAL = (('<i class="fa fa-twitter"></i> @tunnelshade_', 'https://twitter.com/tunnelshade_'),
          ('<i class="fa fa-github"></i> Github', 'https://github.com/tunnelshade'),
          ('<i class="fa fa-linkedin"></i> LinkedIn', 'https://www.linkedin.com/in/tunnelshade/'),
          ('<i class="fa fa-envelope"></i> domain_without_tld@gmail.com', 'domain_without_tld@gmail.com'),)

DEFAULT_PAGINATION = 5
PAGINATION_PATTERNS = (
        (1, '{base_name}/', '{base_name}/index.html'),
        (2, '{base_name}/page/{number}/', '{base_name}/page/{number}/index.html'),)

# Uncomment following line if you want document-relative URLs when developing
THEME = 'hackish'
RELATIVE_URLS = True


# Dont' display categories on Menu
DISPLAY_CATEGORIES_ON_MENU = False
DISPLAY_PAGES_ON_MENU = False

ARTICLE_PATHS = ['blog']
ARTICLE_URL = 'blog/{date:%Y}/{date:%m}/{slug}/'
ARTICLE_SAVE_AS = 'blog/{date:%Y}/{date:%m}/{slug}/index.html'
INDEX_SAVE_AS = 'blog/index.html'

PAGE_PATHS = ['pages']
PAGE_URL = '{slug}/'
PAGE_SAVE_AS = '{slug}/index.html'

TAG_URL = 'tag/{slug}/'
TAG_SAVE_AS = 'tag/{slug}/index.html'
TAGS_URL = 'tags/'
TAGS_SAVE_AS = 'tags/index.html'

AUTHOR_URL = 'author/{slug}/'
AUTHOR_SAVE_AS = 'author/{slug}/index.html'
AUTHORS_URL = 'authors/'
AUTHORS_SAVE_AS = 'authors/index.html'

CATEGORY_URL = 'category/{slug}/'
CATEGORY_SAVE_AS = 'category/{slug}/index.html'
CATEGORYS_URL = 'categories/'
CATEGORYS_SAVE_AS = 'categories/index.html'

STATIC_PATHS = ['images']

GANALYTICS_DOMAIN = None
GANALYTICS_TRACKING_ID = None

DISQUS_SITENAME = None

