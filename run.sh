#!/bin/bash

source venv/bin/activate

#python3 src/ytb2audiobot/ytb2audiobot.py --keepfiles=1

python3 src/ytb2audiobot/ytb2audiobot_asynced.py --keepfiles=1

ytb2audiobot_asynced.py

