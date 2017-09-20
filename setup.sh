#!/bin/bash
virtualenv -p python2.7 virt-hurricanemap
source virt-hurricanemap/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate
