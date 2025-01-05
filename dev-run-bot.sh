#!/bin/bash

#pip install -e . && ytb2audiobot --mode DEV
pip install -e . --no-deps

export $(grep -v '^#' .env | xargs)

ytb2audiobot 2>&1 | tee -a output.log
