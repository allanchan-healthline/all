#!/bin/bash

# Logging
LOG_START_TIME=$(date '+%Y-%m-%d-%H-%M-%S')
SCRIPT_NAME=$(basename $0)
LOG_FILE_NAME="/home/kumiko/logs/${LOG_START_TIME}_${SCRIPT_NAME/.sh/.log}"
echo "${LOG_START_TIME} Start" > $LOG_FILE_NAME

# Main
export PATH="/usr/local/anaconda3/bin:$PATH"
export PYTHONPATH="/home/kumiko/python_path"

DIR="/home/kumiko/weekly_runs"

python $DIR/clean_gdrive4allergan_report.py

python $DIR/clean_gdrive4dcm_reports.py

rm /home/kumiko/pickles/pickles4allergan_dcm_p2/*

rm /home/kumiko/daily_runs/DAS\ Agg\ Backup/*

NOW="$(date)"
YEAR=$(date -d "$NOW" '+%Y')
MONTH=$(date -d "$NOW" '+%m')
cd "/home/kumiko/pickles/lots_of_pickles_${YEAR}_${MONTH}"
ls -r dfp_check_*.pickle | tail -n +2 | xargs rm --

# Logging
LOG_END_TIME=$(date '+%Y-%m-%d-%H-%M-%S')
echo "${LOG_END_TIME} End" >> $LOG_FILE_NAME
mv $LOG_FILE_NAME "${LOG_FILE_NAME}_done"
