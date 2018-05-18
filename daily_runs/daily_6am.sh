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

python send2adjuster.py

A=-1
D=-1
#P=-1
Y=-1

COUNT=0
#while [[ $A != 0 || $D != 0 || $P != 0 || $Y != 0 ]]
while [[ $A != 0 || $D != 0 || $Y != 0 ]]
do
    echo "$(date '+%Y-%m-%d-%H-%M-%S') While loop COUNT=${COUNT} Start" >> $LOG_FILE_NAME
    if [ $A != 0 ] 
    then
        python allergan_report4gsheet.py
        A=$?
    fi

    if [ $D != 0 ]
    then
        python dcm_reports4gdrive.py
        D=$?
    fi

#    if [ $P != 0 ]
#    then
#        python p2_reports4gdrive.py
#        P=$?
#    fi

    if [ $Y != 0 ]
    then
        python dfp_imps4allergan_gsheet.py
        Y=$?
    fi

    # Break out of loop if all is good
    #if [[ $A == 0 && $D == 0 && $P == 0 && $Y == 0 ]]
    if [[ $A == 0 && $D == 0 && $Y == 0 ]]
    then
        break
    fi

    # Wait 5 minutes
    COUNT=$((COUNT+1))
    if [ $COUNT == 5 ]
    then
        break
    fi

    sleep 300
done

# Logging
LOG_END_TIME=$(date '+%Y-%m-%d-%H-%M-%S')
echo "${LOG_END_TIME} End" >> $LOG_FILE_NAME
mv $LOG_FILE_NAME "${LOG_FILE_NAME}_done"
