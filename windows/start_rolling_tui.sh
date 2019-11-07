#!/usr/bin/bash
echo Move to rolling directory
cd ~/rolling
echo Activate python virtual env
source venv/bin/activate
echo Start rolling
python ./rolling-gui.py
