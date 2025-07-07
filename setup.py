import os
import re
import setuptools

NAME = "auntie-sounds"
AUTHOR = "Kieran Hogg"
AUTHOR_EMAIL = "kieran.hogg@gmail.com"
DESCRIPTION = "A module for interacting with BBC Radio stations and streams"
LICENSE = "Apache License 2.0"
KEYWORDS = "BBC Sounds streaming radio API"
URL = "https://github.com/kieranhogg/" + NAME
README = "README.md"
CLASSIFIERS = [
    "Programming Language :: Python :: 3",
]
INSTALL_REQUIRES = []
ENTRY_POINTS = {}
SCRIPTS = []

HERE = os.path.dirname(__file__)


def read(file):
    with open(os.path.join(HERE, file), "r") as fh:
        return fh.read()


VERSION = re.search(
    r'__version__ = [\'"]([^\'"]*)[\'"]', read(NAME.replace("-", "_") + "/__init__.py")
).group(1)

LONG_DESCRIPTION = read(README)

if __name__ == "__main__":
    setuptools.setup(
        name=NAME,
        version=VERSION,
        packages=setuptools.find_packages(),
        author=AUTHOR,
        description=DESCRIPTION,
        license=LICENSE,
        keywords=KEYWORDS,
        url=URL,
        classifiers=CLASSIFIERS,
        install_requires=INSTALL_REQUIRES,
        entry_points=ENTRY_POINTS,
        scripts=SCRIPTS,
        include_package_data=True,
    )
