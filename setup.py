#!/usr/bin/env python

# Always prefer setuptools over distutils
# To use a consistent encoding
from codecs import open
from os import path

from setuptools import setup

# The directory containing this file
HERE = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(HERE, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

with open(path.join(HERE, "requirements.txt"), encoding="utf-8") as f:
    install_requires = f.read().split("\n")


setup(
    name="an_at_sync",
    version="0.4.0",
    description="Python package & cli for syncing between ActionNetwork & AirTable",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="James DiGioia",
    author_email="jamesorodig@gmail.com",
    url="https://github.com/mAAdhaTTah/an-at-sync",
    license="MIT",
    classifiers=[
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    packages=["an_at_sync"],
    install_requires=install_requires,
    entry_points={
        "console_scripts": ["an_at_sync=an_at_sync.cli:main"],
    },
)
