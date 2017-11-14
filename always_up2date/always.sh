#!/bin/bash

# root path for AdBook
ROOT=$(dirname $(dirname "$(readlink -f "$0")"))

# Logging
LOG_START_TIME=$(date '+%Y-%m-%d-%H-%M-%S')
SCRIPT_NAME=$(basename $0)
LOG_FILE_NAME="${ROOT}/logs/${LOG_START_TIME}_${SCRIPT_NAME/.sh/.log}"

echo "${LOG_START_TIME} Start" > $LOG_FILE_NAME

# Main
export PATH="/usr/local/anaconda3/bin:$PATH"
export PYTHONPATH="${ROOT}/python_path"

DIR="${ROOT}/always_up2date"
cd $DIR

for YEAR_MO in "2017_11" "2017_10"
do
    echo "$(date '+%Y-%m-%d-%H-%M-%S') For loop YEAR_MO=${YEAR_MO} Start" >> $LOG_FILE_NAME
    RUNNING="running_$YEAR_MO"
    if [ -f $RUNNING ]
    then
        :
    else
        touch $RUNNING
        FILE="always_up2date_$YEAR_MO.py"
        python $FILE
        rm $RUNNING
    fi
done

# Logging
LOG_END_TIME=$(date '+%Y-%m-%d-%H-%M-%S')
echo "${LOG_END_TIME} End" >> $LOG_FILE_NAME
mv $LOG_FILE_NAME "${LOG_FILE_NAME}_done"
