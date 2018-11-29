#!/bin/bash 

if [ ! -d node_modules/ol/src/ol ]; then
    echo "FATAL: Install dependencies first!"
    echo "npm install"
    exit 1
fi 

if [ ! -d @types/ol ]; then 
    mkdir -p @types/ol
else 
    rm -rf @types/ol/*
fi 

python3 copy-temp-files.py
python3 compile-declaration-files.py
# make a copy for quick-fix only
cp -R @types/ @types_tmp/
python3 hot-fix-content.py
# remove files after hot-fixing
# (use of typedefs in original js files)
python3 remove-temporary-files.py