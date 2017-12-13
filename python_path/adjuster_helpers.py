from NEW_helpers import *

from googleads import dfp
from googleads import errors

import os
import csv
import pandas as pd

from datetime import datetime, date

#######################################################################
# Helper functions
#######################################################################

creative_name2oli_pattern = re.compile('_[0-9]{4}$')
def pick_oli(creative_name):
    if creative_name2oli_pattern.search(creative_name):
        return 'OLI-' + creative_name[-4:]
    else:
        return None

#######################################################################
# TradeDesk 1st party
#######################################################################

def get_tradedesk_report(path_adjuster_report):

    #######################################################################
    # Import and fix formatting
    #######################################################################

    df = pd.read_csv(path_adjuster_report, skiprows=8, encoding='utf-8')

    # Imps are in str format. Convert to int
    df['Impressions'] = [int(imp.replace(',', '')) if isinstance(imp, str) else 0 for imp in df['Impressions']]

    # Date formatting
    df['Report Start Date'] = pd.to_datetime(df['Report Start Date']).dt.date

    #######################################################################
    # Group by (Creative Name, Date)
    #######################################################################

    groupby_col = ['Advertiser', 'Order Name', 'Campaign Name', 'Creative Name', 'Report Start Date']
    df = df[groupby_col + ['Impressions', 'Clicks']].drop_duplicates()
    df = df.groupby(groupby_col).sum().reset_index()

    return df

def label_tradedesk_report(tradedesk_report):

    df = tradedesk_report.copy()

    #######################################################################
    # Label with Salesforce info
    #######################################################################

    df['OLI'] = df['Creative Name'].apply(pick_oli)

    das = make_das(False, False)
    df = pd.merge(df, das[['OLI', 'BBR', 'Line Description']], how='left', on='OLI')

    #######################################################################
    # Extract creative size
    #######################################################################

    creative_name2size_pattern = re.compile('[0-9]+x[0-9]+')
    def pick_size(creative_name):
        size_in_name = creative_name2size_pattern.search(creative_name)
        if size_in_name:
            return size_in_name.group(0)
        else:
            return 'Unknown'
    df['Creative size'] = df['Creative Name'].apply(pick_size)

    #######################################################################
    # Site & Imp Type
    #######################################################################

    df['Site'] = 'TradeDesk'
    df['Imp Type'] = 'TEMP CPM'

    #######################################################################
    # Clean up to match DFP report header
    #######################################################################

    col_rename_dict = {'Order Name': 'Order',
                       'Campaign Name': 'Line item',
                       'Creative Name': 'Creative',
                       'Report Start Date': 'Date',
                       'Impressions': 'Total impressions',
                       'Clicks': 'Total clicks',
                       'BBR': '(Order)BBR #',
                       'Line Description': 'DAS Line Item Name'}

    df = df.rename(columns=col_rename_dict)

    return df

#######################################################################
# Group raw Adjuster report by
# mapping column, 3rd Party Name, Date
#######################################################################

def get_grouped_aj3rd(path_adjuster_report, for_1st_party):

    if for_1st_party == 'DFP':
        map_col = 'Creative Identifier'  # DFP creative id
    elif for_1st_party == 'TTD':
        map_col = 'Creative Name'  # TradeDesk creative name

    #######################################################################
    # Pick up warning
    #######################################################################

    aj_warning = None

    try:
        with open(path_adjuster_report, 'r') as f:
            reader = csv.reader(f)

            for row in reader:
                if len(row) > 0:
                    if row[0] == 'Report Warning:':
                        aj_warning = row[1]
    except IOError as e:
        print('data error: {}'.format(e))
        print('data error: file:', path_adjuster_report)
        print('data error: Type:', for_1st_party)

    if aj_warning is not None:
        aj_warning = aj_warning[aj_warning.index(':') + 1:]
        aj_warning_dict = {}
        for each_aj_warning in aj_warning.split(','):
            each_aj_warning = each_aj_warning.strip()
            server_name = each_aj_warning[:each_aj_warning.index('(') - 1]
            exclude_date = each_aj_warning[each_aj_warning.index('(') + 1: each_aj_warning.index(')')]
            exclude_date = datetime.strptime(exclude_date, '%m/%d/%Y').date()
            aj_warning_dict[server_name] = exclude_date

    #######################################################################
    # Import and fix formatting
    #######################################################################

    df = pd.read_csv(path_adjuster_report, skiprows=8, encoding='utf-8')

    # Imps are in str format. Convert to int. Set invalid str to NaN
    df['Impressions (3rd Party)'] = pd.to_numeric(df['Impressions (3rd Party)'].str.replace(',', ''), errors='coerce')

    # Date formatting
    df['Report Start Date'] = pd.to_datetime(df['Report Start Date']).dt.date

    #######################################################################
    # Group by (map col, 3rd Party Name, Date)
    #######################################################################

    groupby_col = [map_col, '3rd Party Name', 'Report Start Date']
    df = df[groupby_col + ['Impressions (3rd Party)']]
    df = df.groupby(groupby_col).sum().reset_index()

    #######################################################################
    # Exclude ones in warning
    #######################################################################

    if aj_warning is not None:
        for server_name in aj_warning_dict:
            df.loc[(df['3rd Party Name'] == server_name) &
                   (df['Report Start Date'] >= aj_warning_dict[server_name]),
                   'AJ Warning'] = 1

        df = df[df['AJ Warning'] != 1].drop('AJ Warning', axis=1)

    return df

#######################################################################
# Get a mapping DFP report
#######################################################################

def get_dfp_map(start_date, end_date):

    output_file_name = 'temp_dfp_map.csv'

    # Report query id
    saved_query_id = '10004299282'

    # Initialize a client
    client = dfp.DfpClient.LoadFromStorage(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/googleads.yaml")

    # Initialize appropriate service.
    report_service = client.GetService('ReportService', version='v201705')

    # Initialize a DataDownloader.
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

            try:
                # Run the report and wait for it to finish.
                report_job_id = report_downloader.WaitForReport(report_job)
            except errors.DfpReportError as e:
                print('Failed to generate report. Error was: %s' % e)

            # Download report data.
            with open(output_file_name, 'wb') as report_file:
                report_downloader.DownloadReportToFile(report_job_id, 'CSV_DUMP', report_file, use_gzip_compression=False)

        else:
            print('The query specified is not compatible with the API version.')

    # Clean up
    cols = ['Dimension.CREATIVE_ID',
            'Dimension.ORDER_NAME',
            'CF[6995]_Value']

    col_rename_dict = {'Dimension.CREATIVE_ID': 'DFP Creative ID',
                       'Dimension.ORDER_NAME': 'Order',
                       'CF[6995]_Value': 'DAS Line Item Name'}

    df = pd.read_csv(output_file_name, encoding='utf-8')
    df = df[cols].rename(columns=col_rename_dict)

    os.remove(output_file_name)

    return df

#######################################################################
# Add BBR and Line Description to grouped Adjuster report
# via DFP Creative ID
#######################################################################

def get_labeled_grouped_aj3rd_for_dfp(grouped_aj3rd):

    start_date = grouped_aj3rd['Report Start Date'].min()
    end_date = grouped_aj3rd['Report Start Date'].max()

    cid2bbr_daslin = get_dfp_map(start_date, end_date)
    cid2bbr_daslin['BBR'] = [(order[-6:] if ('BBR' in order.upper()) else None) for order in cid2bbr_daslin['Order']]
    cid2bbr_daslin = cid2bbr_daslin.drop('Order', axis=1).drop_duplicates()
    cid2bbr_daslin = cid2bbr_daslin.rename(columns={'DFP Creative ID': 'Creative Identifier'})

    df = pd.merge(grouped_aj3rd, cid2bbr_daslin, how='left', on='Creative Identifier')

    return df

#######################################################################
# Add BBR and Line Description to grouped Adjuster report
# via OLI
#######################################################################

def get_labeled_grouped_aj3rd_for_ttd(grouped_aj3rd):

    df = grouped_aj3rd.copy()
    df['OLI'] = df['Creative Name'].apply(pick_oli)

    das = make_das(False, False)
    df = pd.merge(df, das[['OLI', 'BBR', 'Line Description']], how='left', on='OLI')
    df = df.rename(columns={'Line Description': 'DAS Line Item Name'})

    return df

#######################################################################
# Group labeled & grouped Adjuster report by
# BBR, Line Description, 3rd Party Name, Date
#######################################################################

def get_formatted_aj3rd(labeled_grouped_aj3rd):

    groupby_col = ['BBR', 'DAS Line Item Name', '3rd Party Name', 'Report Start Date']

    df = labeled_grouped_aj3rd[groupby_col + ['Impressions (3rd Party)']]
    df = df.groupby(groupby_col).sum().reset_index()
    df = df.rename(columns={'Report Start Date': 'Date'})

    return df

#######################################################################
# Pick up billable 3rd party imps
#######################################################################

def get_billable_aj3rd(formatted_aj3rd):

    df = formatted_aj3rd.copy()

    start_date = df['Date'].min()
    mo = start_date.month
    year = start_date.year
    das_month = str(mo) + '/' + str(year)
    das = make_das(False, False)
    das_thismonth = das[das[das_month] > 0].rename(columns={'Line Description': 'DAS Line Item Name'})

    join_on = ['BBR', 'DAS Line Item Name']
    df = pd.merge(df, das_thismonth[join_on + ['Billable Reporting Source']], how='left', on=join_on)

    source_dict = {'DCM (fka DFA)': 'DFA',
                   'DV - GroupM': 'DoubleVerify_GroupM',
                   'IAS': 'IAS',
                   'Medialets': 'Medialets',
                   'Moat - Allergan': 'Moat - Allergan',
                   'Sizmek': 'Sizmek',
                   'Teads': 'Teads'}

    def mark_billable(row):
        sf_source = row['Billable Reporting Source']
        if sf_source not in source_dict:
            return 0
        else:
            if source_dict[sf_source] in row['3rd Party Name']:
                return 1
            else:
                return 0

    df['Billable'] = df.apply(lambda row: mark_billable(row), axis=1)

    col = ['BBR', 'DAS Line Item Name', 'Date', 'Impressions (3rd Party)']
    df = df[df['Billable'] == 1][col]

    return df
