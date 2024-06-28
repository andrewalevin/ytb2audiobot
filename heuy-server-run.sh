#!/bin/bash

source venv/bin/activate

huey_consumer.py heuy_taskmanager.huey -k process -w 4
