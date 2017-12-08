from path2pickles import *
from monthly_setup_2017_12 import *

from NEW_helpers import *
from dataflow_class_W_ADJUSTER import *

import os
import shutil

from datetime import datetime, date, timedelta

########################################################################

mo, year = MO_YEAR
DIR_PICKLES = PATH2PICKLES + '/' + PREFIX4ALWAYS_UP2DATE + str(year) + '_' + str(mo).zfill(2)

########################################################################

dir_pythonpath_list = os.environ['PYTHONPATH'].split(os.pathsep)
if dir_pythonpath_list[0].startswith('C:'):  # If Windows
    dir_pythonpath = dir_pythonpath_list[-1].replace('\\', '/')
else:
    dir_pythonpath = dir_pythonpath_list[0]

monthly_setup = dir_pythonpath + '/' + 'monthly_setup_' + str(year) + '_' + str(mo).zfill(2) + '.py'
monthly_setup_last_modified = get_last_modified_local(monthly_setup)

monthly_setup_last_checked_file = 'monthly_setup_' + str(year) + '_' + str(mo).zfill(2) + '_last_checked'
monthly_setup_last_checked = get_last_modified_local(monthly_setup_last_checked_file)

if (monthly_setup_last_checked is None) or (monthly_setup_last_checked < monthly_setup_last_modified):
    if os.path.exists(DIR_PICKLES):
        for f in os.listdir(DIR_PICKLES):
            if f.startswith('dfp_check_'):
                continue
            if f == 'dfp_mtd_all_raw.pickle':
                continue
            os.remove(DIR_PICKLES + '/' + f)

with open(monthly_setup_last_checked_file, 'w') as f:
    pass

########################################################################

check_and_make_dir(DIR_PICKLES)

for var in ['PARTNER_CAPPING_SP_CASE', 'ADD_SPECIAL_CASE']:
    path_name_pickle = DIR_PICKLES + '/' + var.lower() + '.pickle'
    if var in globals():
        with open(path_name_pickle, 'wb') as f:
            pickle.dump(globals()[var], f)
    elif os.path.exists(path_name_pickle):
        os.remove(path_name_pickle)

########################################################################

DataFlow.DIR_PICKLES = DIR_PICKLES
DataFlow.MONTHLY_SHEET_NAME = MONTHLY_SHEET_NAME
DataFlow.UV_TRACKER_GSHEET = UV_TRACKER_GSHEET
DataFlow.MNT_UV_TRACKER_TABS = MNT_UV_TRACKER_TABS
DataFlow.UV_TRACKER_RENAME_DICT = UV_TRACKER_RENAME_DICT
DataFlow.LS_CORRECT_RATE_DICT = LS_CORRECT_RATE_DICT
DataFlow.DRUGS_CORRECT_RATE_LIST = DRUGS_CORRECT_RATE_LIST
DataFlow.TEMP_FIX_DAS4FLAT_FEE = TEMP_FIX_DAS4FLAT_FEE

########################################################################
# Main
########################################################################

yesterday_date = datetime.now().date() - timedelta(days=1)

if mo < yesterday_date.month:
    last_delivery_date = start_end_month(date(year, mo, 1))[1]
else:
    last_delivery_date = yesterday_date

RunThisTo(last_delivery_date, None, None).update_has_changed_dict()

for name in HAS_CHANGED:
    print(name, HAS_CHANGED[name])

print('')

if not HAS_CHANGED['something']:
    print('nothing changed')
else:
    print('something changed')
