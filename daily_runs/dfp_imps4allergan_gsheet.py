from NEW_helpers import *
from gsheet_gdrive_api import *

import sys
import os

from googleads import dfp
from googleads import errors

from datetime import datetime, timedelta
import pandas as pd
import openpyxl as opx

###############################################
# Prep
###############################################

end_date = datetime.now().date() - timedelta(days=1)
start_date = end_date.replace(day=1)
str_start_date = str(start_date.year) + str(start_date.month).zfill(2) + str(start_date.day).zfill(2)
str_end_date = str(end_date.year) + str(end_date.month).zfill(2) + str(end_date.day).zfill(2)

###############################################
# Check if a file for this date range exists
# in the Allergan Report folder in Google Drive
# If not, exit with code 5
###############################################

###############################################
folder_id = '0B71ox_2Qc7gmSS1fbUJKTXEyams'
###############################################

gsheet_name = 'allergan_report_' + str_start_date + '_' + str_end_date
gsheet_id = gdrive_get_file_id_by_name(gsheet_name, folder_id)

if gsheet_id is None:
    sys.exit(5)

###############################################
# Get BBR #s for Allergan
###############################################

das = make_das(use_scheduled_units=False, export=False)
allergan_cpm_paid_das = das[(das['Account Name'] == 'Allergan') &
                            (das[str(start_date.month)+'/'+str(start_date.year)] > 0) &
                            (das['Price Calculation Type'] == 'CPM') &
                            (das['Sales Price'] > 0)]

list_bbr = allergan_cpm_paid_das['BBR'].drop_duplicates().tolist()

###############################################
# Get a list of DFP orders (name, id)
###############################################

# Initialize a client
client = dfp.DfpClient.LoadFromStorage()

# Get all order names and ids
order_service = client.GetService('OrderService', version='v201705')
statement = dfp.FilterStatement()

order_dict = {}
while True:
    response = order_service.getOrdersByStatement(statement.ToStatement())
    if 'results' in response:
        for order in response['results']:
            order_dict[order['name']] = order['id']
        statement.offset += dfp.SUGGESTED_PAGE_LIMIT
    else:
        break

###############################################
# Find order ids for Allergan
###############################################

list_order_id = []
for order_name in order_dict:
    if 'BBR' in order_name:
        for bbr in list_bbr:
            if order_name[-6:] == bbr:
                list_order_id.append(str(order_dict[order_name]))
                break

###############################################
# Get a DFP report for Allergan
###############################################

# CVS file name
output_file_name = 'temp_dfp_for_allergan.csv'

# Report query id
saved_query_id = '10004116057'

# Initialize appropriate service
report_service = client.GetService('ReportService', version='v201705')

# Initialize a DataDownloader
report_downloader = client.GetDataDownloader(version='v201705')

# Create statement object to filter for an order.
values = [{'key': 'id',
           'value': {'xsi_type': 'NumberValue',
                     'value': saved_query_id}}]
query = 'WHERE id = :id'
statement = dfp.FilterStatement(query, values, 1)

response = report_service.getSavedQueriesByStatement(statement.ToStatement())

if 'results' in response:
    saved_query = response['results'][0]

    if saved_query['isCompatibleWithApiVersion']:
        report_job = {}

        # Set report query and optionally modify it.
        report_job['reportQuery'] = saved_query['reportQuery']

        report_job['reportQuery']['startDate']['year'] = start_date.year
        report_job['reportQuery']['startDate']['month'] = start_date.month
        report_job['reportQuery']['startDate']['day'] = start_date.day

        report_job['reportQuery']['endDate']['year'] = end_date.year
        report_job['reportQuery']['endDate']['month'] = end_date.month
        report_job['reportQuery']['endDate']['day'] = end_date.day

        report_job['reportQuery']['statement']['query'] = 'where order_id in (' + ', '.join(list_order_id) + ')'

        try:
            # Run the report and wait for it to finish
            report_job_id = report_downloader.WaitForReport(report_job)
        except errors.DfpReportError as e:
            print('Failed to generate report. Error was: %s' % e)

        # Download report data
        with open(output_file_name, 'wb') as report_file:
            report_downloader.DownloadReportToFile(report_job_id, 'CSV_DUMP', report_file, use_gzip_compression=False)

    else:
        print('The query specified is not compatible with the API version.')

# Clean up
cols = ['Dimension.ORDER_NAME',
        'CF[6995]_Value',
        'Column.TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS']

col_rename_dict = {'Dimension.ORDER_NAME': 'Order',
                   'CF[6995]_Value': 'Line Description',
                   'Column.TOTAL_LINE_ITEM_LEVEL_IMPRESSIONS': 'Total impressions'}

dfp_delivery = pd.read_csv(output_file_name, encoding='utf-8')
dfp_delivery = dfp_delivery[cols].rename(columns=col_rename_dict)

# Delete the csv file
os.remove(output_file_name)

###############################################
# Format data to upload
###############################################

dfp_delivery['BBR'] = [order[-6:] for order in dfp_delivery['Order']]
dfp_delivery = dfp_delivery[['BBR', 'Line Description', 'Total impressions']]
dfp_delivery = dfp_delivery.groupby(['BBR', 'Line Description']).sum().reset_index()

dfp4gsheet = pd.merge(allergan_cpm_paid_das, dfp_delivery, how='left', on=['BBR', 'Line Description'])
dfp4gsheet['Site'] = [ld.split()[0] for ld in dfp4gsheet['Line Description']]
dfp4gsheet.loc[dfp4gsheet['Site'] == 'D', 'Site'] = 'Drugs'
dfp4gsheet = dfp4gsheet[['Site', 'Brand', 'Total impressions']]

###############################################
# Upload to Allergan Report Google Sheet
# on the summary tab
###############################################

service = get_gsheet_service()
result = service.spreadsheets().values().get(
    spreadsheetId=gsheet_id, range='summary', valueRenderOption='UNFORMATTED_VALUE').execute()
values = result.get('values', [])
gsheet = pd.DataFrame(values)
gsheet.columns = gsheet.iloc[0]
gsheet = gsheet[1:]

col_letter = opx.utils.get_column_letter(gsheet.columns.tolist().index('DFP Imps') + 1)

upload_data = []
for site, advertiser, imps in dfp4gsheet.values.tolist():
    i_row = gsheet[(gsheet['Site'] == site) &
                   (gsheet['Advertiser'] == advertiser) &
                   (gsheet['Device'] == 'Total')].index.tolist()[0] + 1
    upload_data.append({'range': 'summary!' + col_letter + str(i_row),
                        'majorDimension': 'ROWS',
                        'values': [[imps]]})

result = service.spreadsheets().values().batchUpdate(
    spreadsheetId=gsheet_id, body={'valueInputOption': 'USER_ENTERED', 'data': upload_data}).execute()
