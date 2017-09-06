#!/bin/bash

# Logging
LOG_START_TIME=$(date '+%Y-%m-%d-%H-%M-%S')
SCRIPT_NAME=$(basename $0)
LOG_FILE_NAME="/home/kumiko/logs/${LOG_START_TIME}_${SCRIPT_NAME/.sh/.log}"
echo "${LOG_START_TIME} Start" > $LOG_FILE_NAME

# Main
export PATH="/usr/local/anaconda3/bin:$PATH"
export PYTHONPATH="/home/kumiko/python_path"

DIR="/home/kumiko/daily_runs"

python $DIR/clean_gdrive4today_dfp_report.py

# Logging
LOG_END_TIME=$(date '+%Y-%m-%d-%H-%M-%S')
echo "${LOG_END_TIME} End" >> $LOG_FILE_NAME
mv $LOG_FILE_NAME "${LOG_FILE_NAME}_done"

