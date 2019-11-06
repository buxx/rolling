#!/usr/bin/env bash

# Make python3 available as python if python2 is not installed
/usr/sbin/update-alternatives --install /usr/bin/python3 python3 $(/usr/bin/find /usr/bin -maxdepth 1 -name "python3.*" -print -quit) 1
/usr/sbin/update-alternatives --install /usr/bin/python  python  $(/usr/bin/find /usr/bin -maxdepth 1 -name "python3.*" -print -quit) 1
