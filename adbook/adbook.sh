#!/bin/bash

# root path for AdBook
ROOT=$(dirname $(dirname $0))

export PATH="/usr/local/anaconda3/bin:$PATH"
export PYTHONPATH="${ROOT}/python_path"

DIR="${ROOT}/adbook"
cd $DIR

NOW="$(date)"
YEAR=$(date -d "$NOW" '+%Y')
MONTH=$(date -d "$NOW" '+%m')
DAY=$(date -d "$NOW" '+%d')

python check4all1_n_sgoals_n_3rdpimps.py $YEAR $MONTH
CHECK=$?

if [ $CHECK == 7 ]
then
    touch last_run_${YEAR}_${MONTH}   
    python update_adbook.py $YEAR $MONTH
    aws s3 sync adbook_${YEAR}_${MONTH} s3://healthline-ad-book-v2/adbook_${YEAR}_${MONTH} --delete
fi

# continue update of the old adbook for the first 10 days of the month
# to catch up on data is was dated on the previous month.
if [ "$DAY" -lt 10 ]
then
    LASTMONTH_YEAR=$(date -d "$YEAR-$MONTH-15 last month" '+%Y')
    LASTMONTH_MONTH=$(date -d "$YEAR-$MONTH-15 last month" '+%m')

    python check4all1_n_sgoals_n_3rdpimps.py $LASTMONTH_YEAR $LASTMONTH_MONTH
    CHECK=$?

    if [ $CHECK == 7 ]
    then
        touch last_run_${LASTMONTH_YEAR}_${LASTMONTH_MONTH}
        python update_adbook.py $LASTMONTH_YEAR $LASTMONTH_MONTH
        aws s3 sync adbook_${LASTMONTH_YEAR}_${LASTMONTH_MONTH} s3://healthline-ad-book-v2/adbook_${LASTMONTH_YEAR}_${LASTMONTH_MONTH} --delete
    fi
fi
