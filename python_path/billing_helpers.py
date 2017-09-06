from path2pickles import *
from NEW_helpers import *
from delivery_helpers import *
from gsheet_gdrive_api import *

import pickle
import pandas as pd
import openpyxl as opx

from datetime import date

pd.options.mode.chained_assignment = None


##############################################################
# Billing Grid
##############################################################

def make_bg_as_csv(year, mo):

    ##############################################################
    # Prep
    ##############################################################

    output_file_name = 'for_billing_grid_' + str(year) + '_' + str(mo).zfill(2) + '.csv'

    start_date = date(year, mo, 1)
    end_date = start_end_month(start_date)[1]

    def convert2dcm_date(date_obj):
        return str(date_obj.year) + '-' + str(date_obj.month).zfill(2) + '-' + str(date_obj.day).zfill(2)

    start_date = convert2dcm_date(start_date)
    end_date = convert2dcm_date(end_date)

    ##############################################################
    # CPM DFP imps
    ##############################################################
        
    DIR_PICKLES = PATH2PICKLES + '/' + PREFIX4ALWAYS_UP2DATE + str(year) + '_' + str(mo).zfill(2)
    with open(DIR_PICKLES + '/' + 'all1.pickle', 'rb') as f:
        all1 = pickle.load(f)
    
    all1_cpm = all1[all1['Price Calculation Type'] == 'CPM'].rename(columns={'Impressions/UVs': 'First Party Units'})
    
    bbr_brand_li = ['(DAS)BBR #', 'Brand', 'DAS Line Item Name']
    dfp_imps = all1_cpm[bbr_brand_li + ['First Party Units']].groupby(bbr_brand_li).sum().reset_index()

    ##############################################################
    # DCM imps
    ##############################################################

    all_data, profiles_df, grouped_all_data = dcm_reporting(start_date, end_date)

    groupby_col = ['Placement ID']
    value_col = ['Impressions']
    rename_dict = {'Placement ID': '3rd Party Creative ID', 'Impressions': 'DFA(by ID)'}
    dcm_imps = all_data[groupby_col + value_col].groupby(groupby_col).sum().reset_index().rename(columns=rename_dict)
    dcm_imps['3rd Party Creative ID'] = [str(id) for id in dcm_imps['3rd Party Creative ID']]
    
    dfp_dcm_map = all1_cpm[bbr_brand_li + ['3rd Party Creative ID']].drop_duplicates()
    dcm_imps = pd.merge(dfp_dcm_map, dcm_imps, how='left', on='3rd Party Creative ID')
    dcm_imps = dcm_imps[bbr_brand_li + ['DFA(by ID)']].groupby(bbr_brand_li).sum().reset_index()

    ##############################################################
    # Select Billing Grid data from DAS
    ##############################################################

    das = make_das(use_scheduled_units=False, export=False)
    das_month = str(mo) + '/' + str(year)
    
    bg = das[das[das_month] > 0]
    bg = bg[bg['Price Calculation Type'] != 'CPA']

    ##############################################################
    # Multi-Month Bill Up To
    ##############################################################
    
    das_header = das.columns.tolist()
    months_list = []
    for col in das_header:
        if re.search('[0-9]+/[0-9]{4}', col):
            months_list.append(col)

    (das_month_mo, das_month_year) = das_month.split('/')
    das_month_mo = int(das_month_mo)
    das_month_year = int(das_month_year)

    months = []
    for month in months_list:
        (mo, year) = month.split('/')
        mo = int(mo)
        year = int(year)
        if year < das_month_year:
            continue
        elif year > das_month_year:
            months.append(month)
        elif mo >= das_month_mo:
                months.append(month)

    for month in months:
        bg[month].fillna(0, inplace=True)

    bg['Multi-Month Bill Up To'] = bg.apply(lambda row: sum(round(row[month], 0) for month in months), axis=1)
    bg.loc[bg['Flight Type'] == 'Monthly', 'Multi-Month Bill Up To'] = ''

    ##############################################################
    # Rename columns
    ##############################################################

    rename_dict = {'Brand': 'Advertiser', 
                   'IO Number': 'Purchase Order / Insertion Order',
                   'Line Description': 'Placement', 
                   'Price Calculation Type': 'Rate Type', 
                   'Sales Price': 'Rate', 
                   das_month: 'Booked Impressions', 
                   'Flight Type': 'Goal Breakdown', 
                   'Account Manager': 'AM', 
                   'Campaign Manager': 'CM',
                   'Billable Reporting Source': 'Third Party System'}
    
    bg = bg.rename(columns=rename_dict)

    ##############################################################
    # Add CPM DFP and DCM imps
    ##############################################################

    imps_rename_dict = {'(DAS)BBR #': 'BBR', 'Brand': 'Advertiser', 'DAS Line Item Name': 'Placement'}
    imps_join_on = ['BBR', 'Advertiser', 'Placement']

    bg = pd.merge(bg, dfp_imps.rename(columns=imps_rename_dict), how='left', on=imps_join_on)
    bg = pd.merge(bg, dcm_imps.rename(columns=imps_rename_dict), how='left', on=imps_join_on)

    ##############################################################
    # Add columns to be manually entered or calculated with formulas
    ##############################################################

    bg['Billed Units'] = ''
    bg['Total Cost'] = ''
    bg['110%'] = ''
    bg['Discrepancy'] = ''
    bg['Third Party Impressions'] = ''
    bg['Check DFA'] = ''
    bg['Overbilling Check'] = ''
    bg['Delivery to Booked Check'] = ''
    bg['DAS Cost'] = ''
    bg['Actual Cost'] = ''
    bg['DAS v Actual Cost'] = ''
    bg['Hit the goal?'] = ''
    bg['UD'] = ''
    bg['UD $'] = ''
    bg['Confirmed?'] = 0

    ##############################################################
    # Sort
    ##############################################################

    header = ['OLI', 'Advertiser', 'Agency', 'Campaign Name', 'Purchase Order / Insertion Order', 'Line Item Number',
              'Placement', 'Rate Type', 'Rate', 'Billed Units', 'Total Cost', 'Booked Impressions', '110%', 'Multi-Month Bill Up To',
              'Discrepancy', 'First Party Units', 'Third Party Impressions', 'DFA(by ID)', 'Check DFA', 'Third Party System',
              'Goal Breakdown', 'AM', 'CM', 'BBR', 'DAS Cost', 'Actual Cost',
              'DAS v Actual Cost', 'Hit the goal?', 'UD', 'UD $', 'Confirmed?', 'Stage']

    sortby = ['Advertiser', 'Campaign Name', 'BBR', 'Line Item Number', 'Placement']

    bg = bg[header].sort_values(sortby).reset_index(drop=True)

    ##############################################################
    # Formulas
    ##############################################################

    def col_name2col_letter(col_name):
        col_num = header.index(col_name) + 1
        return opx.utils.get_column_letter(col_num)

    col_third_party_system = col_name2col_letter('Third Party System')
    col_goal_breakdown = col_name2col_letter('Goal Breakdown')
    col_booked_imps = col_name2col_letter('Booked Impressions')
    col_first_party_units = col_name2col_letter('First Party Units')
    col_110 = col_name2col_letter('110%')
    col_multimonth_billupto = col_name2col_letter('Multi-Month Bill Up To')
    col_third_party_imps = col_name2col_letter('Third Party Impressions')
    col_rate_type = col_name2col_letter('Rate Type')
    col_billed_units = col_name2col_letter('Billed Units')
    col_rate = col_name2col_letter('Rate')
    col_total_cost = col_name2col_letter('Total Cost')
    col_actual_cost = col_name2col_letter('Actual Cost')
    col_das_cost = col_name2col_letter('DAS Cost')
    col_ud = col_name2col_letter('UD')
    col_dfa_byid = col_name2col_letter('DFA(by ID)')

    def get_billed_units(i):
        row = str(i + 2)
        output = '=ROUND(IF(' + col_third_party_system + row + '="DFP", '
        output += 'IF(' + col_goal_breakdown + row + '="Monthly", MIN(' + col_booked_imps + row + ', ' + col_first_party_units + row + '), '
        output += 'MIN(' + col_110 + row + ', ' + col_multimonth_billupto + row + ', ' + col_first_party_units + row + ')), '
        output += 'IF(' + col_goal_breakdown + row + '="Monthly", MIN(' + col_booked_imps + row + ', ' + col_third_party_imps + row + '), '
        output += 'MIN(' + col_110 + row + ', ' + col_multimonth_billupto + row + ', ' + col_third_party_imps + row + '))), 0)'
        return output

    def get_total_cost(i):
        row = str(i + 2)
        output = '=IF(OR(' + col_rate_type + row + '="CPM", ' + col_rate_type + row + '="AV-CPM"), '
        output += col_billed_units + row + '/1000*' + col_rate + row + ', '
        output += col_billed_units + row + '*' + col_rate + row + ')'
        return output

    def get_110(i):
        row = str(i + 2)
        return '=IF(' + col_goal_breakdown + row + '<>"Monthly", ' + col_booked_imps + row + '*1.1, "")'

    def get_das_cost(i):
        row = str(i + 2)
        output = '=IF(OR(' + col_rate_type + row + '="CPM", ' + col_rate_type + row + '="AV-CPM"), '
        output += col_booked_imps + row + '/1000*' + col_rate + row + ', '
        output += col_booked_imps + row + '*' + col_rate + row + ')'
        return output

    def get_actual_cost(i):
        row = str(i + 2)
        return '=' + col_total_cost + row

    def get_dasvactual_cost(i):
        row = str(i + 2)
        return '=' + col_actual_cost + row + '-' + col_das_cost + row

    def get_hit_goal(i):
        row = str(i + 2)
        return '=IF(' + col_billed_units + row + '>=' + col_booked_imps + row + ', 1, 0)'

    def get_ud(i):
        row = str(i + 2)
        output = '=IF(' + col_booked_imps + row + '-' + col_billed_units + row + '>0, '
        output += col_booked_imps + row + '-' + col_billed_units + row + ', 0)'
        return output

    def get_ud_amount(i):
        row = str(i + 2)
        output = '=IF(OR(' + col_rate_type + row + '="CPM", ' + col_rate_type + row + '="AV-CPM"), '
        output += col_ud + row + '/1000*' + col_rate + row + ', '
        output += col_ud + row + '*' + col_rate + row + ')'
        return output

    def get_discrepancy(i):
        row = str(i + 2)
        output = '=IF(' + col_third_party_system + row + '="DFP", 0, '
        output += '(' + col_first_party_units + row + '-' + col_third_party_imps + row + ')/' + col_first_party_units + row + ')'
        return output

    def get_check_dfa(i):
        row = str(i + 2)
        output = '=IF(ISNUMBER(FIND("DCM", ' + col_third_party_system + row + ')), '
        output += col_third_party_imps + row + '=' + col_dfa_byid + row + ', "")'
        return output

    bg['Billed Units'] = [get_billed_units(i) for i in range(len(bg))]
    bg['Total Cost'] = [get_total_cost(i) for i in range(len(bg))]
    bg['110%'] = [get_110(i) for i in range(len(bg))]
    bg['DAS Cost'] = [get_das_cost(i) for i in range(len(bg))]
    bg['Actual Cost'] = [get_actual_cost(i) for i in range(len(bg))]
    bg['DAS v Actual Cost'] = [get_dasvactual_cost(i) for i in range(len(bg))]
    bg['Hit the goal?'] = [get_hit_goal(i) for i in range(len(bg))]
    bg['UD'] = [get_ud(i) for i in range(len(bg))]
    bg['UD $'] = [get_ud_amount(i) for i in range(len(bg))]
    bg['Discrepancy'] = [get_discrepancy(i) for i in range(len(bg))]
    bg['Check DFA'] = [get_check_dfa(i) for i in range(len(bg))]

    bg.loc[bg['Rate Type'] != 'CPM', ('Discrepancy', 'Check DFA')] = ('', '')

    ##############################################################
    # Grand Total row
    ##############################################################

    last_row = str(len(bg) + 1)
    total_row_df = pd.DataFrame(index=[0], columns=bg.columns.tolist())

    # Subtotal
    subtotal_col_name_list = ['Billed Units',
                              'Total Cost',
                              'Booked Impressions',
                              '110%',
                              'Multi-Month Bill Up To',
                              'First Party Units',
                              'Third Party Impressions',
                              'DFA(by ID)',
                              'DAS Cost',
                              'Actual Cost',
                              'DAS v Actual Cost',
                              'Hit the goal?',
                              'UD',
                              'UD $',
                              'Confirmed?']

    for col_name in subtotal_col_name_list:
        col_letter = col_name2col_letter(col_name)
        total_row_df[col_name] = '=SUBTOTAL(9, ' + col_letter + '2:' + col_letter + last_row + ')'

    # Other
    total_row_df['OLI'] = 'Grand Total'
    total_row_df['Discrepancy'] = '=(' + col_first_party_units + last_row + '-' + col_third_party_imps + last_row + ')/' + col_first_party_units + last_row
    total_row_df['Check DFA'] = '=' + col_third_party_imps + last_row + '=' + col_dfa_byid + last_row

    ##############################################################
    # Output
    ##############################################################

    bg = pd.concat([bg, total_row_df])
    bg.to_csv(output_file_name, index=False)

    return output_file_name

def upload_bg2gdrive(year, mo, csv_file_name):

    #################################################
    folder_id = '0B71ox_2Qc7gmWkNWM21YUU9MSEU'
    #################################################

    service = get_gsheet_service()    
    
    # Upload csv to Google Drive as Google Sheet
    month_dict = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}
    gsheet_file_name = month_dict[mo] + ' ' + str(year) + ' Billing Grid'

    file_id = save_csv_as_gsheet_in_gdrive(gsheet_file_name, folder_id, csv_file_name)

    # Change sheet name to BG
    ss_metadata = service.spreadsheets().get(spreadsheetId=file_id).execute()
    s_metadata = ss_metadata['sheets'][0]['properties']
    sheet_id = s_metadata['sheetId']

    change_sheet_name = [{'updateSheetProperties': {'properties': {'sheetId': sheet_id, 'title': 'BG'}, 'fields': 'title'}}]
    result = service.spreadsheets().batchUpdate(spreadsheetId=file_id, body={'requests': change_sheet_name}).execute()

    # Add template BG formatting sheet
    #################################################
    template_ss_id = '1EM3EDQayLgn9MBsmdRnHhFxyq6553Q5waWTzpdzUogE'
    template_s_id = '1207419624'
    #################################################

    request = service.spreadsheets().sheets().copyTo(spreadsheetId=template_ss_id, sheetId=template_s_id, body={'destination_spreadsheet_id': file_id})
    response = request.execute()
    
    return file_id

def format_bg(file_id):

    service = get_gsheet_service()
    
    # Get sheet ids
    s_id_bg = None
    s_id_template = None
    
    ss_metadata = service.spreadsheets().get(spreadsheetId=file_id).execute()
    for s_metadata in ss_metadata['sheets']:
        if s_metadata['properties']['title'] == 'BG':
            s_id_bg = s_metadata['properties']['sheetId']
        if s_metadata['properties']['title'] == 'Copy of template':
            s_id_template = s_metadata['properties']['sheetId']

    # Get values > header, # of rows, # of columns
    result = service.spreadsheets().values().get(
        spreadsheetId=file_id, range='BG', valueRenderOption='UNFORMATTED_VALUE').execute()
    values = result.get('values', [])
    
    header = values[0]
    n_col = len(header)
    n_row = len(values)

    # Header formatting from template
    header_format = [{'copyPaste': {'source': {'sheetId': s_id_template,
                                               'startRowIndex': 0,
                                               'endRowIndex': 1,
                                               'startColumnIndex': 0,
                                               'endColumnIndex': n_col},
                                    'destination': {'sheetId': s_id_bg,
                                                    'startRowIndex': 0,
                                                    'endRowIndex': 1,
                                                    'startColumnIndex': 0,
                                                    'endColumnIndex': n_col},
                                    'pasteType': 'PASTE_FORMAT'}}]


    # Content formatting from template
    content_format = [{'copyPaste': {'source': {'sheetId': s_id_template, 
                                                'startRowIndex': 1,
                                                'endRowIndex': 2,
                                                'startColumnIndex': 0,
                                                'endColumnIndex': n_col},
                                    'destination': {'sheetId': s_id_bg,
                                                    'startRowIndex': 1,
                                                    'endRowIndex': n_row-1,
                                                    'startColumnIndex': 0,
                                                    'endColumnIndex': n_col},
                                    'pasteType': 'PASTE_FORMAT'}}]

    # Footer formatting from template
    footer_format = [{'copyPaste': {'source': {'sheetId': s_id_template,
                                               'startRowIndex': 2,
                                               'endRowIndex': 3,
                                               'startColumnIndex': 0,
                                               'endColumnIndex': n_col},
                                    'destination': {'sheetId': s_id_bg,
                                                    'startRowIndex': n_row-1,
                                                    'endRowIndex': n_row,
                                                    'startColumnIndex': 0,
                                                    'endColumnIndex': n_col},
                                    'pasteType': 'PASTE_FORMAT'}}]

    # Freeze top row and left colums
    freeze = [{'updateSheetProperties': {'properties': {'sheetId': s_id_bg,
                                                        'gridProperties': {'frozenRowCount': 1,
                                                                           'frozenColumnCount': header.index('Placement')+1}},
                                         'fields': 'gridProperties(frozenRowCount, frozenColumnCount)'}}]

    # Add filter
    basic_filter = [{'setBasicFilter': {'filter': {'range': {'sheetId': s_id_bg, 
                                                   'startRowIndex': 0,
                                                   'endRowIndex': n_row-1,
                                                   'startColumnIndex': 0, 
                                                   'endColumnIndex': n_col}}}}]

    # Add a filter view per cm
    i_cm = header.index('CM')
    cms = []
    for i in range(1, len(values)-1):
        cms.append(values[i][i_cm])
    cms = set(cms)

    filter_views = []
    for cm in cms:
        filter_view_name = cm.split()[0].lower()
        filter_view_dict = {'addFilterView': {'filter': {'title': filter_view_name, 
                                                         'range': {'sheetId': s_id_bg,
                                                                   'startRowIndex': 0,
                                                                   'endRowIndex': n_row-1,
                                                                   'startColumnIndex': 0,
                                                                   'endColumnIndex': n_col},
                                                         'criteria': {i_cm: {'condition': {'type': 'TEXT_EQ', 
                                                                                           'values': [{'userEnteredValue': cm}]}}}}}}
        filter_views.append(filter_view_dict)

    # Column width
    width = []
    for col in header:
        if col == 'OLI':
            size = 55
        elif col == 'Campaign Name':
            size = 140
        elif col == 'Line Item Number':
            size = 50
        elif col == 'Placement':
            size = 200
        else:
            size = 90

        width_dict = {'updateDimensionProperties': {'range': {'sheetId': s_id_bg,
                                                              'dimension': 'COLUMNS',
                                                              'startIndex': header.index(col),
                                                              'endIndex': header.index(col)+1},
                                                    'properties': {'pixelSize': size},
                                                    'fields': 'pixelSize'}}
        width.append(width_dict)

    # Send requests
    all_requests = header_format + content_format + footer_format
    all_requests += freeze + basic_filter + filter_views + width

    result = service.spreadsheets().batchUpdate(spreadsheetId=file_id, body={'requests': all_requests}).execute()

    # Delete formatting template sheet
    result = service.spreadsheets().batchUpdate(spreadsheetId=file_id, body={'requests': [{'deleteSheet': {'sheetId': s_id_template}}]}).execute()
   
 
##############################################################
# Ask.com TP
##############################################################

def make_ask_tp_as_excel(year, mo):
   
    ############################################################## 
    # Prep
    ##############################################################

    output_file_name = 'for_ask_tp_' + str(year) + '_' + str(mo).zfill(2) + '.xlsx'
    
    ##############################################################
    # Get data
    ##############################################################

    # Labeled dfp report
    DIR_PICKLES = PATH2PICKLES + '/' + PREFIX4ALWAYS_UP2DATE + str(year) + '_' + str(mo).zfill(2)
    with open(DIR_PICKLES + '/' + 'all1.pickle', 'rb') as f:
        all1 = pickle.load(f)
    
    df = all1[pd.notnull(all1['Ad unit'])]  # Only include DFP data, no UV data

    # Extract Ask TP imps
    df = df[df['Site'] == 'HL']

    df.loc[(df['Ad unit'].str.contains('ask', case=False) & df['Ad unit'].str.contains('tp', case=False)), 'Ask TP Domain'] = 'Ask.com'
    df.loc[df['Ad unit'].str.contains('.ask'), 'Ask TP Domain'] = 'Ask.com'
    df.loc[df['Ad unit'].str.contains('.sas'), 'Ask TP Domain'] = 'Search.Ask.com'
    df.loc[df['Ad unit'].str.contains('.mwy'), 'Ask TP Domain'] = 'MyWay.com'
    
    df = df[pd.notnull(df['Ask TP Domain'])]

    ##############################################################
    # Main sheet
    ##############################################################

    # Format
    groupby_col = ['Ask TP Domain', 'Ad unit', 'Price Calculation Type', 'Advertiser', 'Order', 'Line item', 'Base Rate']
    value_col = ['Impressions/UVs']
    rename_dict = {'Base Rate': 'Rate', 'Impressions/UVs': 'Impressions'}

    for col in groupby_col:
        df.loc[pd.isnull(df[col]), col] = 'N/A'

    df = df[groupby_col + value_col].groupby(groupby_col).sum().reset_index().rename(columns=rename_dict)

    # Add Revenue Type
    def add_rev_type(row):
        if row['Price Calculation Type'] == 'CPM':
            return 'DAS'
        if row['Advertiser'] in ['Programmatic Partners', 'OpenX']:
            return 'Programmatic'
        if row['Advertiser'].startswith('Prebid'):
            return 'Prebid'
        return ''

    df['Revenue Type'] = df.apply(lambda row: add_rev_type(row), axis=1)

    # Add Gross Revenue, to be populated with excel formula
    df['Gross Revenue'] = ''

    # Clean up
    header = ['Ask TP Domain', 'Ad unit', 'Advertiser', 'Order', 'Line item', 'Revenue Type', 'Rate', 'Impressions', 'Gross Revenue']
    sortby = ['Ask TP Domain', 'Advertiser', 'Order', 'Line item', 'Rate']
    df = df[header].sort_values(sortby).reset_index(drop=True)

    # Add formula for Rate
    order_col_letter = opx.utils.get_column_letter(header.index('Order') + 1)

    def update_rate(row):
        if row['Revenue Type'] == 'DAS':
            return row['Rate']
        if row['Revenue Type'] == 'Programmatic':
            str_row_num = str(row.name + 2)
            return "=VLOOKUP(" + order_col_letter + str_row_num + ",'Programmatic eCPMs'!$A:$B,2,FALSE)"
        if row['Revenue Type'] == 'Prebid':
            return "='Prebid eCPMs'!B1"
        return 0

    df['Rate'] = df.apply(lambda row: update_rate(row), axis=1)

    # Add formula for Revenue
    imps_col_letter = opx.utils.get_column_letter(header.index('Impressions') + 1)
    rate_col_letter = opx.utils.get_column_letter(header.index('Rate') + 1)

    df['Gross Revenue'] = ['=' + imps_col_letter + str(i+2) + '/1000*' + rate_col_letter + str(i+2) for i in range(len(df))]

    ##############################################################
    # eCPM sheets
    ##############################################################

    # Sheet for Programmatic eCPMs (To be filled in by Chris later, average eCPM per DFP Order)
    df_prog = df[df['Revenue Type'] == 'Programmatic'][['Order']].drop_duplicates().sort_values(['Order'])
    df_prog['eCPM'] = None

    # Sheet for Prebid eCPMs (To be filled in by Chris later, average eCPM of all)
    df_prebid = pd.DataFrame(columns=['Average'])

    ##############################################################
    # Write to excel
    ##############################################################

    writer = pd.ExcelWriter(output_file_name)
    df.to_excel(writer, 'main', index=False)
    df_prog.to_excel(writer, 'Programmatic eCPMs', index=False)
    df_prebid.to_excel(writer, 'Prebid eCPMs', index=False)
    writer.save()

    return output_file_name

def upload_ask_tp2gdrive(year, mo, excel_file_name):
    
    ##############################################################
    folder_id = '0B71ox_2Qc7gmSFBTUjctXzJMRFU'
    ##############################################################

    gsheet_file_name = 'Ask.com_TP_' + str(year) + '_' +  str(mo).zfill(2)
    
    file_id = save_excel_as_gsheet_in_gdrive(gsheet_file_name, folder_id, excel_file_name)

    return file_id

def format_ask_tp(file_id):

    service = get_gsheet_service()

    ##############################################################
    # Make a dictionary of basic sheet info
    ##############################################################

    sheet_dict = {}

    ss_metadata = service.spreadsheets().get(spreadsheetId=file_id).execute()
    for s_metadata in ss_metadata['sheets']:
        # Sheet name and id
        sheet_name = s_metadata['properties']['title']
        sheet_id = s_metadata['properties']['sheetId'] 

        # Get values > header, # of col, # of row
        result = service.spreadsheets().values().get(
            spreadsheetId=file_id, range=sheet_name, valueRenderOption='UNFORMATTED_VALUE').execute()
        values = result.get('values', [])

        header = values[0]
        n_col = len(header)
        n_row = len(values)

        # Store as a tuple
        sheet_dict[sheet_name] = (sheet_id, header, n_col, n_row)        

    ##############################################################
    # Helper functions etc.
    ##############################################################

    def make_vf_dict(sheet_name, col, format_type):
        sheet_id, header, n_col, n_row = sheet_dict[sheet_name]
        i_col = header.index(col)

        if format_type == 'integer':
            pattern = '###,###,##0'
        elif format_type == 'dollar':
            pattern = '$#,###,##0.00'
        
        return {'repeatCell': {'range': {'sheetId': sheet_id,
                                         'startRowIndex': 1,
                                         'endRowIndex': n_row,
                                         'startColumnIndex': i_col,
                                         'endColumnIndex': i_col+1},
                               'cell': {'userEnteredFormat': {'numberFormat': {'type': 'NUMBER',
                                                                               'pattern': pattern}}},
                               'fields': 'userEnteredFormat.numberFormat'}}
    
    # color dicts
    green = {'red': .851, 'green': .918, 'blue': .827, 'alpha': 1}
    yellow = {'red': 1, 'green': .949, 'blue': .8, 'alpha': 1}

    def make_color_header_list(sheet_name):
        sheet_id, header, n_col, n_row = sheet_dict[sheet_name]

        return [{'updateCells': {'rows': [{'values': [{'userEnteredFormat': {'backgroundColor': green}}] * n_col}],
                                 'fields': 'userEnteredFormat.backgroundColor',
                                 'range': {'sheetId': sheet_id,
                                           'startRowIndex': 0,
                                           'endRowIndex': 1,
                                           'startColumnIndex': 0,
                                           'endColumnIndex': n_col}}}]

    ##############################################################
    # Format main sheet
    ##############################################################

    sheet_name = 'main'
    sheet_id, header, n_col, n_row = sheet_dict[sheet_name]

    # Freeze top row
    freeze = [{'updateSheetProperties': {'properties': {'sheetId': sheet_id,
                                                        'gridProperties': {'frozenRowCount': 1}},
                                         'fields': 'gridProperties(frozenRowCount)'}}]

    # Add filter
    basic_filter = [{'setBasicFilter': {'filter': {'range': {'sheetId': sheet_id,
                                                   'startRowIndex': 0,
                                                   'endRowIndex': n_row,
                                                   'startColumnIndex': 0,
                                                   'endColumnIndex': n_col}}}}]

    # Wrap header
    wrap = [{'updateCells': {'rows': [{'values': [{'userEnteredFormat': {'wrapStrategy': 'WRAP'}}] * n_col}],
                             'fields': 'userEnteredFormat.wrapStrategy',
                             'range': {'sheetId': sheet_id,
                                       'startRowIndex': 0,
                                       'endRowIndex': 1,
                                       'startColumnIndex': 0,
                                       'endColumnIndex': n_col}}}]
    
    # Color header
    color = make_color_header_list(sheet_name)

    # Value formatting
    value_formatting = []
    value_formatting.append(make_vf_dict(sheet_name, 'Rate', 'dollar'))
    value_formatting.append(make_vf_dict(sheet_name, 'Impressions', 'integer'))
    value_formatting.append(make_vf_dict(sheet_name, 'Gross Revenue', 'dollar'))

    # Width
    width = [{'updateDimensionProperties': {'range': {'sheetId': sheet_id,
                                                      'dimension': 'COLUMNS',
                                                      'startIndex': 0,
                                                      'endIndex': n_col},
                                            'properties': {'pixelSize': 90},
                                            'fields': 'pixelSize'}}]
   
    # Clip
    clip = [{'updateCells': {'rows': [{'values': [{'userEnteredFormat': {'wrapStrategy': 'CLIP'}}] * n_col}] * (n_row-1),
                             'fields': 'userEnteredFormat.wrapStrategy',
                             'range': {'sheetId': sheet_id,
                                       'startRowIndex': 1,
                                       'endRowIndex': n_row,
                                       'startColumnIndex': 0,
                                       'endColumnIndex': n_col}}}]
 
    # Send requests
    requests = freeze + basic_filter + wrap + color + value_formatting + width + clip
    result = service.spreadsheets().batchUpdate(spreadsheetId=file_id, body={'requests': requests}).execute()

    ##############################################################
    # Format programmatic sheet
    ##############################################################

    sheet_name = 'Programmatic eCPMs'
    sheet_id, header, n_col, n_row = sheet_dict[sheet_name]

    # Color header
    color_header = make_color_header_list(sheet_name)

    color_rates = [{'updateCells': {'rows': [{'values': [{'userEnteredFormat': {'backgroundColor': yellow}}]}] * (n_row-1),
                                   'fields': 'userEnteredFormat.backgroundColor',
                                   'range': {'sheetId': sheet_id,
                                             'startRowIndex': 1,
                                             'endRowIndex': n_row,
                                             'startColumnIndex': 1,
                                             'endColumnIndex': 2}}}]

    # Value formatting
    value_formatting = []
    value_formatting.append(make_vf_dict(sheet_name, 'eCPM', 'dollar'))

    # Width
    width = [{'updateDimensionProperties': {'range': {'sheetId': sheet_id,
                                                      'dimension': 'COLUMNS',
                                                      'startIndex': 0,
                                                      'endIndex': 1},
                                            'properties': {'pixelSize': 240},
                                            'fields': 'pixelSize'}}]

    # Send requests
    requests = color_header + color_rates + value_formatting + width
    result = service.spreadsheets().batchUpdate(spreadsheetId=file_id, body={'requests': requests}).execute()

    ##############################################################
    # Format prebid sheet
    ##############################################################

    sheet_name = 'Prebid eCPMs'
    sheet_id, header, n_col, n_row = sheet_dict[sheet_name]

    # Color header, just cell A1
    # Color cell for Chris, just cell B1
    color = [{'updateCells': {'rows': [{'values': [{'userEnteredFormat': {'backgroundColor': green}}, 
                                                   {'userEnteredFormat': {'backgroundColor': yellow}}]}],
                              'fields': 'userEnteredFormat.backgroundColor',
                              'range': {'sheetId': sheet_id,
                                        'startRowIndex': 0,
                                        'endRowIndex': 1,
                                        'startColumnIndex': 0,
                                        'endColumnIndex': 2}}}]

    # Value formatting
    value_formatting = [{'repeatCell': {'range': {'sheetId': sheet_id,
                                        'startRowIndex': 0,
                                        'endRowIndex': 1,
                                        'startColumnIndex': 1,
                                        'endColumnIndex': 2},
                         'cell': {'userEnteredFormat': {'numberFormat': {'type': 'NUMBER',
                                                                                 'pattern': '$#,###,##0.00'}}},
                         'fields': 'userEnteredFormat.numberFormat'}}]

    # Send requests
    requests = color + value_formatting 
    result = service.spreadsheets().batchUpdate(spreadsheetId=file_id, body={'requests': requests}).execute()

    ##############################################################
    # Create summary sheet (piv table of main sheet)
    # Reference: https://developers.google.com/sheets/api/samples/pivot-tables
    ##############################################################
    
    # Source sheet info
    sheet_id, header, n_col, n_row = sheet_dict['main']

    # Create summary sheet and move to far left
    piv_sheet_id =  gsheet_create_sheet('summary', file_id)
    move = [{'updateSheetProperties': {'properties': {'sheetId': piv_sheet_id, 
                                                      'index': 0}, 
                                       'fields': 'index'}}]

    # Insert pivot table
    pivt = [{'updateCells': {'rows': {'values': [{'pivotTable': {'source': {'sheetId': sheet_id,
                                                                            'startRowIndex': 0,
                                                                            'endRowIndex': n_row,
                                                                            'startColumnIndex': 0,
                                                                            'endColumnIndex': n_col},
                                                                 'rows': [{'sourceColumnOffset': header.index('Ask TP Domain'),
                                                                           'showTotals': True,
                                                                           'sortOrder': 'ASCENDING',
                                                                           'valueBucket': {'buckets': [{'stringValue': 'Ask TP Domain'}]}},
                                                                          {'sourceColumnOffset': header.index('Revenue Type'),
                                                                           'showTotals': True,
                                                                           'sortOrder': 'ASCENDING',
                                                                           'valueBucket': {'buckets': [{'stringValue': 'Revenue Type'}]}}],
                                                                 'values': [{'summarizeFunction': 'SUM',
                                                                             'sourceColumnOffset': header.index('Impressions')},
                                                                            {'summarizeFunction': 'SUM',
                                                                             'sourceColumnOffset': header.index('Gross Revenue')}],
                                                                 'valueLayout': 'HORIZONTAL'}}]},
                             'start': {'sheetId': piv_sheet_id,
                                       'rowIndex': 0,
                                       'columnIndex': 0},
                             'fields': 'pivotTable'}}]

    requests = move + pivt
    result = service.spreadsheets().batchUpdate(spreadsheetId=file_id, body={'requests': requests}).execute()


