#!/bin/bash

source venv/bin/activate

dramatiq --processes 3 --threads 1 dramatiq
