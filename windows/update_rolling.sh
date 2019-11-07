#!/bin/bash
echo Move to rolling directory
cd ~/rolling
git pull origin
echo Activate python virtual env
source venv/bin/activate
echo Update python dependencies
pip install -e ".[tui]"
echo Update rolling
python setup.py develop
echo Update finished
