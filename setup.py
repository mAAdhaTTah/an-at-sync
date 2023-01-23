#!/usr/bin/env python

from setuptools import setup

setup(
    name="an_at_sync",
    version="1.0",
    description="ActionNetwork to AirTable CLI",
    author="James DiGioia",
    author_email="jamesorodig@gmail.com",
    # url="https://www.python.org/sigs/distutils-sig/",
    packages=["an_at_sync"],
    entry_points={
        "console_scripts": ["an_at_sync=an_at_sync.cli:main"],
    },
)
