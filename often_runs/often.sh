#!/bin/bash

# Logging
LOG_START_TIME=$(date '+%Y-%m-%d-%H-%M-%S')
SCRIPT_NAME=$(basename $0)
LOG_FILE_NAME="/home/kumiko/logs/${LOG_START_TIME}_${SCRIPT_NAME/.sh/.log}"
echo "${LOG_START_TIME} Start" > $LOG_FILE_NAME

# Main
export PATH="/usr/local/anaconda3/bin:$PATH"
export PYTHONPATH="/home/kumiko/python_path"

DIR="/home/kumiko/often_runs"
cd $DIR

NOW="$(date)"
YEAR=$(date -d "$NOW" '+%Y')
MONTH=$(date -d "$NOW" '+%m')
DAY=$(date -d "$NOW" '+%d')

echo "$(date '+%Y-%m-%d-%H-%M-%S') YEAR=${YEAR} & MONTH=${MONTH} Start" >> $LOG_FILE_NAME

python check4all1_n_sgoals.py $YEAR $MONTH
CHECK=$?

if [[ $CHECK == 7 || $CHECK == 8 ]]
then
    touch "last_run_${YEAR}_${MONTH}"   
    if [ $CHECK == 7 ]
    then
        python nr2gsheet_n_gdrive.py $YEAR $MONTH
        python clean_gdrive4nr.py
        python check_mapping2gsheet.py $YEAR $MONTH
        python uvs2gsheet.py $YEAR $MONTH
    fi
    python hw_rev_rep2gdrive.py $YEAR $MONTH
    python clean_gdrive4hw_rev_rep.py
fi

if [ "$DAY" -lt 10 ]
then
    LASTMONTH_YEAR=$(date -d "$YEAR-$MONTH-15 last month" '+%Y')
    LASTMONTH_MONTH=$(date -d "$YEAR-$MONTH-15 last month" '+%m')

    echo "$(date '+%Y-%m-%d-%H-%M-%S') YEAR=${LASTMONTH_YEAR} & MONTH=${LASTMONTH_MONTH} Start" >> $LOG_FILE_NAME

    python check4all1_n_sgoals.py $LASTMONTH_YEAR $LASTMONTH_MONTH
    CHECK=$?

    if [[ $CHECK == 7 || $CHECK == 8 ]]
    then
        touch "last_run_${LASTMONTH_YEAR}_${LASTMONTH_MONTH}"
        if [ $CHECK == 7 ]
        then
            python nr2gsheet_n_gdrive.py $LASTMONTH_YEAR $LASTMONTH_MONTH
            python clean_gdrive4nr.py
            python check_mapping2gsheet.py $LASTMONTH_YEAR $LASTMONTH_MONTH
            python uvs2gsheet.py $LASTMONTH_YEAR $LASTMONTH_MONTH
        fi
        python hw_rev_rep2gdrive.py $LASTMONTH_YEAR $LASTMONTH_MONTH
        python clean_gdrive4hw_rev_rep.py
    fi
fi

# Logging
LOG_END_TIME=$(date '+%Y-%m-%d-%H-%M-%S')
echo "${LOG_END_TIME} End" >> $LOG_FILE_NAME
mv $LOG_FILE_NAME "${LOG_FILE_NAME}_done"

