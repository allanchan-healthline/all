#!/bin/bash

# root path for AdBook
ROOT=$(dirname $(dirname "$(readlink -f "$0")"))

# Logging
TODAY=`date '+%Y%m%d'`
STATUS=${ROOT}/logs/${0##*/}.$TODAY.log
echo "[`date '+%Y-%m-%d %H:%M:%S.%s'`] Starting $0" > $STATUS

# Main
export PATH="/usr/local/anaconda3/bin:$PATH"
export PYTHONPATH="${ROOT}/python_path"

DIR="${ROOT}/always_up2date"
cd $DIR

CURRENT_MONTH=`date "+%Y_%m"`
PREVIOUS_MONTH=`date -d "- 1 month" "+%Y_%m"`

for YEAR_MO in ${PREVIOUS_MONTH} ${CURRENT_MONTH} 
do
    echo "[`date '+%Y-%m-%d %H:%M:%S.%s'`] For loop YEAR_MO=${YEAR_MO} Start" >> $STATUS
    RUNNING="running_$YEAR_MO"
    if [ -f $RUNNING ]
    then
        :
    else
        touch $RUNNING
        FILE="always_up2date_$YEAR_MO.py"
        python $FILE >> $STATUS 2>&1
        rm $RUNNING
    fi
done

# Logging
echo "[`date '+%Y-%m-%d %H:%M:%S.%s'`] Ended $0" >> $STATUS
