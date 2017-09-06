from delivery_helpers import *
from NEW_helpers import *

import os
import pandas as pd
from datetime import datetime, timedelta

############################################
folder_id = '0B71ox_2Qc7gmaGZjRjlCYjR3QXc'
############################################

yesterday_date = datetime.now().date() - timedelta(days=1)
month_start_date = yesterday_date.replace(day=1)
report_start_date = str(month_start_date.year) + '-' + str(month_start_date.month).zfill(2) + '-' + str(month_start_date.day).zfill(2)
report_end_date = str(yesterday_date.year) + '-' + str(yesterday_date.month).zfill(2) + '-' + str(yesterday_date.day).zfill(2)

(all_data, profiles_df, grouped_all_data) = dcm_reporting(report_start_date, report_end_date)
file_name = 'DCM_Reports_' + report_start_date + '_' + report_end_date + '.xlsx'
writer = pd.ExcelWriter(file_name)
all_data.to_excel(writer, 'data', index=False)
profiles_df.to_excel(writer, 'profiles', index=False)
grouped_all_data.to_excel(writer, 'grouped', index=False)
writer.save()

save_in_gdrive(file_name, folder_id, 'application/vnd.ms-excel')
os.remove(file_name)