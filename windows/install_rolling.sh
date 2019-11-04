#!/bin/bash

git clone https://github.com/buxx/rolling.git /home/root/rolling
cd /home/root/rolling
python -m venv venv
source venv/bin/activate
pip install -e ".[tui]"
python setup.py develop
