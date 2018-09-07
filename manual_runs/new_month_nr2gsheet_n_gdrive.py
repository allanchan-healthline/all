from monthly_setup_2018_09 import *

from NEW_helpers import *
from always_up2date_helpers import *
from report_helpers import *

import pandas as pd
from datetime import datetime, date

mo, year = MO_YEAR

############################################################################
# Site Goals
############################################################################

pas_sheet = MONTHLY_SHEET_NAME['pas']
cpuv_goals_sheet = MONTHLY_SHEET_NAME['cpuv goals']

site_goals = get_site_goals(MO_YEAR, pas_sheet, cpuv_goals_sheet, LS_CORRECT_RATE_DICT,
                            DRUGS_CORRECT_RATE_LIST, TEMP_FIX_DAS4FLAT_FEE)

############################################################################
# Dummy Daily Site Report
############################################################################

das = make_das(False, False)
das_month = str(mo) + '/' + str(year)
dummy_line = das_filtered(das, das_month).iloc[0]
dummy = {'Price Calculation Type': [dummy_line['Price Calculation Type']],
         'BBR': [dummy_line['BBR']],
         'Brand': [dummy_line['Brand']],
         'DAS Line Item Name': [dummy_line['Line Description']],
         'Site': ['HL'],
         'Date': [date(year, mo, 1)],
         'Delivered': [0],
         'Billable': [0],
         'Clicks': [0]}

daily_site_report = pd.DataFrame(data=dummy)

############################################################################
# Create a new Google Sheet file if not there
############################################################################

folder_id = '0B71ox_2Qc7gmU0dVMDhTUnk3Y0U'

file_name = 'Network_Report_' + str(year) + '_' + str(mo).zfill(2)
file_id = gdrive_get_file_id_by_name(file_name, folder_id)

if file_id is None:
    existing_file_id = gdrive_get_most_recent_file_id(folder_id)
    gdrive_copy_file(existing_file_id, file_name)

############################################################################
# Upload
############################################################################

now = datetime.now()

summary_by_site_dict = get_summary_by_site_dict(daily_site_report, site_goals)

nr2gsheet_dict = {}
nr2gsheet_dict['ss name'] = file_name
nr2gsheet_dict['rev & exp'] = pd.DataFrame(columns=['DAS Price Calculation Type', 'Site Group',	'Site', 'Date',	'Revenue', 'Expense', 'Prod. Fee'])
nr2gsheet_dict['sum by site'] = summary_by_site_dict['grouped']
up_nr2gsheet(nr2gsheet_dict)

nr2gdrive_dict = {}
nr2gdrive_dict['file name'] = 'NR_Data_' + str(year) + '_' + str(mo).zfill(2)
nr2gdrive_dict['file name'] += '_AsOf_' + now.strftime('%m-%d-%Y-%Hhr%Mmin')
nr2gdrive_dict['file name'] += '.xlsx'
nr2gdrive_dict['daily site report'] = pd.DataFrame(columns=['^_^'])
nr2gdrive_dict['raw summary by site'] = summary_by_site_dict['raw']
up_nr2gdrive(nr2gdrive_dict)

