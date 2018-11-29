#!/bin/bash 

# script to reload by copying 
# compiled declaration files
# (need to have .ts sources)
rm -rf @types/ol/*
cp -R @types_tmp/ol/* @types/ol/
python3 hot-fix-content.py
python3 remove-temporary-files.py 