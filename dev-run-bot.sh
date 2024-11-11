#!/bin/bash

#pip install -e . && ytb2audiobot --mode DEV
pip install -e . --no-deps

export YTB2AUDIO_DEBUG_MODE="true"
ytb2audiobot
