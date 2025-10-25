#!/usr/bin/env bash
set -e

# Встановити Python 3.11.9 через pyenv
pyenv install -s 3.11.9
pyenv global 3.11.9

# Встановити залежності
pip install --upgrade pip
pip install -r requirements.txt
