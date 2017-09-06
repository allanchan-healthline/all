from NEW_helpers import *
from delivery_helpers import *
from p2_helpers import *

import os
import pandas as pd
from datetime import datetime, timedelta

############################################################################
# Prep
############################################################################

###########################################
folder_id = '0B71ox_2Qc7gmVVdFYThhMHFfQzg'
###########################################

yesterday_date = datetime.now().date() - timedelta(days=1)
month_start_date = yesterday_date.replace(day=1)
start_date = str(month_start_date.year) + '-' + str(month_start_date.month).zfill(2) + '-' + str(month_start_date.day).zfill(2)
end_date = str(yesterday_date.year) + '-' + str(yesterday_date.month).zfill(2) + '-' + str(yesterday_date.day).zfill(2)

das_month = str(yesterday_date.month) + '/' + str(yesterday_date.year)
das = make_das(use_scheduled_units=False, export=False)
dcm_plmnt_ids = get_dcm_placement_ids(yesterday_date)

daterange = start_date.replace('-', '', 2) + '_' + end_date.replace('-', '', 2)

############################################################################
# Allergan
############################################################################

(o1_original, o2_labeled, o3_summary, o4_only_billable) = allergan_report(start_date.replace('-', '', 2), end_date.replace('-', '', 2))
mtd_revenue_allergan = add_allergan_revenue2delivery(o4_only_billable, das, das_month)

file_name = 'Allergan_MTD_Revenue_' + daterange + '.xlsx'
writer = pd.ExcelWriter(file_name)
camp_rev(mtd_revenue_allergan).to_excel(writer, 'Rev per Camp', index=False)
mtd_revenue_allergan.to_excel(writer, daterange, index=False)
writer.save()

save_in_gdrive(file_name, folder_id, 'application/vnd.ms-excel')
os.remove(file_name)

############################################################################
# DCM campaigns
############################################################################

prep = prep_dcm_sf_linking(dcm_plmnt_ids)
(all_data, profiles_df, grouped_all_data) = dcm_reporting(start_date, end_date)
selected_data = select_camps(all_data)
mtd_revenue_via_dcm = dcm_sf_linking(selected_data, prep, das, das_month)

file_name = 'DCM_MTD_Revenue_' + daterange + '.xlsx'
writer = pd.ExcelWriter(file_name)
camp_rev(mtd_revenue_via_dcm).to_excel(writer, 'Rev per Camp', index=False)
mtd_revenue_via_dcm.to_excel(writer, daterange, index=False)
profiles_df.to_excel(writer, 'profiles', index=False)
writer.save()

save_in_gdrive(file_name, folder_id, 'application/vnd.ms-excel')
os.remove(file_name)