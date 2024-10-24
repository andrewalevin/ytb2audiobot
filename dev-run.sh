#!/bin/bash

#pip install -e . && ytb2audiobot --mode DEV
pip install -e . --no-deps
ytb2audiobot --debug
#ytb2audiobotrouter --debug