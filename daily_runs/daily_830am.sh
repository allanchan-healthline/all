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
cd $DIR

NOW="$(date)"
YEAR=$(date -d "$NOW" '+%Y')
MONTH=$(date -d "$NOW" '+%m')
DAY=$(date -d "$NOW" '+%d')

if [ "$DAY" -lt 10 ]
then
    LASTMONTH_YEAR=$(date -d "$YEAR-$MONTH-15 last month" '+%Y')
    LASTMONTH_MONTH=$(date -d "$YEAR-$MONTH-15 last month" '+%m')
    python das_agg2gsheet_n_gdrive.py $LASTMONTH_YEAR $LASTMONTH_MONTH
fi

python das_agg2gsheet_n_gdrive.py $YEAR $MONTH

# Logging
LOG_END_TIME=$(date '+%Y-%m-%d-%H-%M-%S')
echo "${LOG_END_TIME} End" >> $LOG_FILE_NAME
mv $LOG_FILE_NAME "${LOG_FILE_NAME}_done"
