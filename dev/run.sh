#!/bin/bash

source venv/bin/activate

# python3 src/ytb2audiobot/ytb2audiobot.py --keepfiles=1

pdm run ytb2audiobot --dev

