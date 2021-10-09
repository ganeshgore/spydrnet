#!/bin/bash

python3 -m venv buildenv
source buildenv/bin/activate
python3 -m pip install --upgrade --no-cache-dir pip
python3 -m pip install --upgrade --no-cache-dir \
        mock==1.0.1 \
        pillow==5.4.1 \
        alabaster \
        six \
        commonmark==0.8.1 \
        recommonmark==0.5.0 \
        sphinx==3.4.0 \
        pybtex

pip install -r docs/requirements.txt
cd docs && make html