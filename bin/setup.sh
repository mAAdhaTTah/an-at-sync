#! /usr/bin/env bash

python3 -m venv .venv --prompt=an_at_sync
source .venv/bin/activate
pip install -r requirements.txt -r requirements.dev.txt
pip install .
