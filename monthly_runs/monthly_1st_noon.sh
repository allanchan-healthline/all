#!/bin/bash

# Logging
LOG_START_TIME=$(date '+%Y-%m-%d-%H-%M-%S')
SCRIPT_NAME=$(basename $0)
LOG_FILE_NAME="/home/kumiko/logs/${LOG_START_TIME}_${SCRIPT_NAME/.sh/.log}"
echo "${LOG_START_TIME} Start" > $LOG_FILE_NAME

# Main
export PATH="/usr/local/anaconda3/bin:$PATH"
export PYTHONPATH="/home/kumiko/python_path"

DIR="/home/kumiko/monthly_runs"

python $DIR/clean_gdrive4pacing_report.py

python $DIR/clean_gdrive4p2_reports.py

# Logging
LOG_END_TIME=$(date '+%Y-%m-%d-%H-%M-%S')
echo "${LOG_END_TIME} End" >> $LOG_FILE_NAME
mv $LOG_FILE_NAME "${LOG_FILE_NAME}_done"

