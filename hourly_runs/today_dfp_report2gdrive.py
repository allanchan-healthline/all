from NEW_helpers import *
from delivery_helpers import *

import os

# Create csv
generated_at, df = get_dfp_today_delivery()
csv_name = 'Today_DFP_Report_AsOf_NY_' + generated_at.strftime('%m-%d-%Y_%Hhr%Mmin') + '.csv'
df.to_csv(csv_name, index=False, encoding='utf-8')

# Upload csv to Google Drive
folder_id = '0B71ox_2Qc7gmZDVGaHprRmQ3ajg'
save_in_gdrive(csv_name, folder_id, 'text/csv')

# Delete csv
os.remove(csv_name)