#!/bin/bash

source venv/bin/activate

rm -rf dist/*

python3 -m pip install --upgrade build

python3 -m pip install --upgrade twine

python3 -m build

last_created_file=$(ls -t dist/*.whl | head -n 1)
echo "$last_created_file"

pip install "$last_created_file"


