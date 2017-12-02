from NEW_helpers import *
from delivery_helpers import *

import os

# Create csv
generated_at, df = get_dfp_last_hour_delivery()
csv_name = 'LastHour_DFP_Report_AsOf_NY_' + generated_at.strftime('%m-%d-%Y_%Hhr%Mmin') + '.csv'
df.to_csv(csv_name, index=False, encoding='utf-8')

# Upload csv to Google Drive
folder_id = '1NcDWuBdZAeieXHp4YihaHBD42S0Ra2LB'
save_in_gdrive(csv_name, folder_id, 'text/csv')

# Email if a line delivered over 50k
#email2adops_over50k_last_hour(df)

# Delete csv
os.remove(csv_name)
