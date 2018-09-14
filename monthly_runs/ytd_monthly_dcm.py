from WIP_dcm_report import *
from NEW_helpers import *

import os
import pandas as pd
from datetime import datetime, timedelta

############################################
folder_id = '1Va3DDqQ1IyZfUoZoNQvG_k_YtBXkSno0'
############################################

yesterday_date = datetime.now().date() - timedelta(days=1)
year_start_date = yesterday_date.replace(month=1, day=1)
report_start_date = str(year_start_date.year) + '-' + str(year_start_date.month).zfill(2) + '-' + str(year_start_date.day).zfill(2)
report_end_date = str(yesterday_date.year) + '-' + str(yesterday_date.month).zfill(2) + '-' + str(yesterday_date.day).zfill(2)

(all_data, profiles_df) = ytd_monthly_dcm_reporting_4bizops(report_start_date, report_end_date)
file_name = 'YTD_Monthly_DCM_Reports_4BizOps_' + report_start_date + '_' + report_end_date + '.xlsx'
writer = pd.ExcelWriter(file_name)
all_data.to_excel(writer, 'data', index=False)
profiles_df.to_excel(writer, 'profiles', index=False)
writer.save()

save_in_gdrive(file_name, folder_id, 'application/vnd.ms-excel')
save_excel_as_gsheet_in_gdrive(file_name.replace('.xlsx', ''), folder_id, file_name)
os.remove(file_name)
