#!/bin/bash
echo Move to home directory
cd ~
echo Clone rolling repository
git clone https://github.com/buxx/rolling.git
echo Move to rolling directory
cd ~/rolling
echo Make python virtual env
python -m venv venv
echo Activate python virtual env
source venv/bin/activate
echo Install python dependencies
pip install -e ".[tui]"
echo Install rolling
python setup.py develop
echo Install finished
