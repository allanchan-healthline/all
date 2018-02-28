from NEW_helpers import *
from report_helpers import cap_delivery

from googleads import dfp
from googleads import errors
from gsheet_gdrive_api import *

import os
import pickle

import pandas as pd
import numpy as np
import re
from datetime import datetime, date, timedelta

pd.options.mode.chained_assignment = None  # default='warn'

###################################################################
# CPM
###################################################################

def get_dfp_check(last_delivery_date):
    """Return a dataframe of a MTD DFP report where the Order name contains 'BBR'.
    Fields for the output are:
    ORDER_ID, ORDER_NAME, LINE_ITEM_ID, LINE_ITEM_NAME, CREATIVE_ID, DAS Line Item Name (Custom field for creative)
    """

    start_date = last_delivery_date.replace(day=1)
    end_date = last_delivery_date

    output_file_name = 'temp_dfp_update_check.csv'

    ########################################################
    # Get Order ID, Order Name,
    #     Line Item ID, Line Item Name,
    #     Creative ID, DAS Line Item Name
    ########################################################

    dfp_client = dfp.DfpClient.LoadFromStorage(os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/googleads.yaml")
    filter_statement = {'query': "WHERE ORDER_NAME LIKE '%BBR%'"}

    report_job = {
        'reportQuery': {
            'dimensions': ['ORDER_ID', 'ORDER_NAME',
                           'LINE_ITEM_ID', 'LINE_ITEM_NAME',
                           'CREATIVE_ID'],
            'statement': filter_statement,
            'columns': ['AD_SERVER_IMPRESSIONS'],
            'dateRangeType': 'CUSTOM_DATE',
            'startDate': {'year': start_date.year,
                          'month': start_date.month,
                          'day': start_date.day},
            'endDate': {'year': end_date.year,
                        'month': end_date.month,
                        'day': end_date.day},
            'customFieldIds': [6995]
        }
    }

    report_downloader = dfp_client.GetDataDownloader(version='v201702')
    try:
        report_job_id = report_downloader.WaitForReport(report_job)
    except errors.DfpReportError as e:
        print('Failed to generate report. Error was: %s' % e)

    with open(output_file_name, 'wb') as report_file:
        report_downloader.DownloadReportToFile(report_job_id, 'CSV_DUMP', report_file, use_gzip_compression=False)

    df = pd.read_csv(output_file_name, encoding='utf-8')

    # Remove impressions
    df = df.drop('Column.AD_SERVER_IMPRESSIONS', axis=1)

    os.remove(output_file_name)
    return df

def label_dfp_mtd_all(dfp_mtd_all):
    """Do the following to an input dataframe, and return:
    1. If 'Order' contains 'BBR', extract last 6 characters into '(Order) BBR #'.
    2. Identify non-CPM imps. Add 'Imp Type' for MNT imps (contracts with MNT and not with Healthline), CPA imps, CPUV imps, 
       Flat-fee imps, non-billable imps (in exclude list), test imps, and default imps.
    3. Add 'Site'.
    """

    ###########################################################
    # Prep
    ###########################################################

    dfp_mtd_all['DAS Line Item Name'] = [lin.strip() for lin in dfp_mtd_all['DAS Line Item Name']]

    ###########################################################
    # Identify DAS CPM rows
    ###########################################################

    dfp_mtd_all['(Order)BBR #'] = [(o[-6:] if 'BBR' in o.upper() else 0)
                                   for o in dfp_mtd_all['Order']]
    dfp_mtd_all['Imp Type'] = [('Imp(Other)' if bbr == 0 else 'CPM')
                               for bbr in dfp_mtd_all['(Order)BBR #']]

    # MNT orders
    dfp_mtd_all.loc[[('MNT' in o) for o in dfp_mtd_all['Order']], 'Imp Type'] = 'Imp(MNT)'

    # CPA, CPUV, Flat-fee imps
    dfp_mtd_all.loc[dfp_mtd_all['Line item'].str.contains('_CPA_', case=False), 'Imp Type'] = 'Imp(CPA)'
    dfp_mtd_all.loc[dfp_mtd_all['Line item'].str.contains('_CPUV_', case=False), 'Imp Type'] = 'Imp(CPUV)'
    dfp_mtd_all.loc[dfp_mtd_all['Line item'].str.contains('synvisc', case=False), 'Imp Type'] = 'Imp(CPUV)'
    dfp_mtd_all.loc[dfp_mtd_all['Line item'].str.contains('_Ff_', case=False), 'Imp Type'] = 'Imp(Flat-fee)'

    # Exclude imps
    exclude_list = get_exclude_list()
    exclude_list['Exclude List'] = 1
    dfp_mtd_all = pd.merge(dfp_mtd_all, exclude_list[['Line item', 'Creative', 'Exclude List']],
                           how='left', on=['Line item', 'Creative'])
    dfp_mtd_all.loc[dfp_mtd_all['Exclude List'] == 1, 'Imp Type'] = 'Imp(In Exclude List)'
    dfp_mtd_all = dfp_mtd_all.drop('Exclude List', axis=1)

    # Test imps
    dfp_mtd_all.loc[dfp_mtd_all['Line item'].str.contains('test', case=False) &
                    np.invert(dfp_mtd_all['Line item'].str.contains('contest', case=False)),
                    'Imp Type'] = 'Imp(Test)'

    # Defaults imps
    dfp_mtd_all.loc[dfp_mtd_all['Order'].str.contains('defaults', case=False),
                    'Imp Type'] = 'Imp(Defaults)'

    ###########################################################
    # Add Site from Ad Unit
    ###########################################################

    ask_1 = re.compile('Ask Health')
    ask_2 = re.compile('hn\.us\.ask\.')
    bhm = re.compile('BlackHealthMatters-Direct')
    dailyrx = re.compile('HN US/HMN dailyRX-Direct')
    dr_oz = re.compile('HN US/HMN Dr Oz')
    dr_gourmet = re.compile('Dr. Gourmet-root-1333')
    drugs_1 = re.compile('HN US/HMN Drugs\.com')
    drugs_2 = re.compile('hn\.us\.hmndrg\.')
    ehow = re.compile('eHow_Direct')
    emedtv = re.compile('HN US/HMN eMedTV - Direct')
    empowher = re.compile('HN US/HMN EmpowHer - Direct')
    goodrx = re.compile('Good_RX_Direct')
    livestrong_1 = re.compile('HN US/HMN Livestrong - Direct')
    livestrong_2 = re.compile('hn\.us\.ls\.')
    mnt = re.compile('MNT_Direct')
    patient_info = re.compile('Patient\.Info_Direct')
    rxwiki = re.compile('HN US/HMN RXWiki - Direct')
    skinsight = re.compile('HN US/HMN SkinSight - Direct')
    bco = re.compile('BCO ')

    site_dict = {ask_1: 'Ask', ask_2: 'Ask', bhm: 'Black Health Matters', dailyrx: 'dailyRX', dr_oz: 'Dr Oz',
                 dr_gourmet: 'Dr.Gourmet', drugs_1: 'Drugs.com', drugs_2: 'Drugs.com', ehow: 'eHow',
                 emedtv: 'eMedTV', empowher: 'EmpowHer', goodrx: 'GoodRx', livestrong_1: 'Livestrong',
                 livestrong_2: 'Livestrong', mnt: 'Medical News Today', patient_info: 'Patient Info',
                 rxwiki: 'RxWiki', skinsight: 'SkinSight', bco: 'Breastcancer.org'}

    def add_site(ad_unit):
        for key in site_dict:
            if key.match(ad_unit):
                return site_dict[key]
        return 'HL'

    dfp_mtd_all['Site'] = [add_site(ad_unit) for ad_unit in dfp_mtd_all['Ad unit']]
    dfp_mtd_all.loc[[('MNT' in o) for o in dfp_mtd_all['Order']], 'Site'] = 'Medical News Today'
    dfp_mtd_all.loc[[('MNT' in li) for li in dfp_mtd_all['Line item']], 'Site'] = 'Medical News Today'

    return dfp_mtd_all

###################################################################
# CPUV
###################################################################

def label_microsite_uvs(df, mo_year, cpuv_goals_sheet):
    """Return a dataframe of microsite uvs labeled with Salesforce info.
    """

    if len(df) == 0:
        return pd.DataFrame()
    else:
        site = df['Site'].tolist()[0]

    cpuv_goals = get_cpuv_goals(mo_year[1], cpuv_goals_sheet)

    ###########################################################
    # Indicate entered uvs v.s. empty cell
    ###########################################################

    df['UV entered'] = 1
    df.loc[pd.isnull(df['UVs']), ('UVs', 'UV entered')] = (0, 0)
    df['UVs'] = [(0 if isinstance(uv, str) else int(uv)) for uv in df['UVs']]

    ###########################################################
    # Join with goals sheet
    ###########################################################
    df['Report Tab Name'] = df['Original Report Tab Name']

    if site != 'HL':
        # Change column name if needed
        if site == 'Medical News Today':
            goals_col = 'MNT Report Tab Name'
        elif site == 'Breastcancer.org':
            goals_col = 'BCO Report Tab Name'
        if site in ['Medical News Today', 'Breastcancer.org']:
            cpuv_goals = cpuv_goals.drop('Report Tab Name', axis=1)
            cpuv_goals = cpuv_goals.rename(columns={goals_col: 'Report Tab Name'})

        df = pd.merge(df, cpuv_goals[['BBR', 'Campaign Name', 'Line Description', 'Base Rate', 'Report Tab Name']],
                      how='left', on='Report Tab Name')
    else:
        ###########################################################
        # For HL, check for multiple tabs counted towards a line item
        # (Report Tab Name includes a comma)
        ###########################################################

        str_in_goals_sheet_list = cpuv_goals['HL Report Tab Name'].drop_duplicates().tolist()
        for str_in_goals_sheet in str_in_goals_sheet_list:
            if (str_in_goals_sheet is not None) and (str_in_goals_sheet != ''):
                if ',' in str_in_goals_sheet:
                    for sheet in [s.strip() for s in str_in_goals_sheet.split(',')]:
                        df.loc[df['Original Report Tab Name'] == sheet,
                               ('Original Report Tab Name', 'Report Tab Name')]\
                            = (str_in_goals_sheet, str_in_goals_sheet)

        groupby_col = df.columns.tolist()
        groupby_col.remove('UVs')
        groupby_col.remove('UV entered')
        df = df.groupby(groupby_col).sum().reset_index()

        ###########################################################
        # Add goals sheet info
        ###########################################################

        df = pd.merge(df, cpuv_goals[['BBR', 'Campaign Name', 'Line Description', 'Base Rate', 'HL Report Tab Name']],
                      how='left', left_on='Report Tab Name', right_on='HL Report Tab Name')
        df = df.drop('HL Report Tab Name', axis=1)

        ###########################################################
        # For HL, check for campaigns with paid and av lines
        ###########################################################

        line_count = {}
        for sheet in cpuv_goals['HL Report Tab Name']:
            if (sheet is not None) and (sheet != ''):
                if sheet in line_count:
                    line_count[sheet] += 1
                else:
                    line_count[sheet] = 1

        for sheet in line_count:
            if line_count[sheet] == 1:
                continue

            ###########################################################
            # Calculate paid delivery
            ###########################################################
            paid_goal_list = cpuv_goals[(cpuv_goals['HL Report Tab Name'] == sheet) &
                                        (cpuv_goals['Base Rate'] > 0)]['HL Goal'].tolist()
            av_goal_list = cpuv_goals[(cpuv_goals['HL Report Tab Name'] == sheet) &
                                      (cpuv_goals['Base Rate'] == 0)]['HL Goal'].tolist()

            # Ignore incorrectly entered tab names (on CPUV Goals Sheet)
            if (len(paid_goal_list) == 0) or (len(av_goal_list) == 0):
                continue
  
            paid_goal = paid_goal_list[0] 
            av_goal = av_goal_list[0] 

            total_delivery = df[df['Report Tab Name'] == sheet]['UVs'].sum() / 2
            if total_delivery >= (paid_goal + av_goal):
                paid_delivery = total_delivery - av_goal
            elif total_delivery >= paid_goal:
                paid_delivery = paid_goal
            else:
                paid_delivery = total_delivery

            ###########################################################
            # Adjust
            ###########################################################

            temp_df = df[(df['Report Tab Name'] == sheet) & (df['Base Rate'] > 0)]
            temp_df = cap_delivery(temp_df, paid_delivery, 'UVs')

            daily_both = temp_df['UVs'].tolist()
            daily_paid = temp_df['Capped UVs'].tolist()
            daily_av = [daily_both[i] - daily_paid[i] for i in range(len(daily_both))]

            df.loc[(df['Report Tab Name'] == sheet) & (df['Base Rate'] > 0),
                   'UVs'] = daily_paid
            df.loc[(df['Report Tab Name'] == sheet) & (df['Base Rate'] == 0),
                   'UVs'] = daily_av

    return df

def label_cc_uvs(df, mo_year, cpuv_goals_sheet):
    """Return a dataframe of competitive conquesting uvs labeled with Salesforce info."""

    # site = df['Site'].tolist()[0]

    cpuv_goals = get_cpuv_goals(mo_year[1], cpuv_goals_sheet)
    cc_p_report_list = cpuv_goals['CC Partner Report'].tolist()
    df_site_gsrange_col_list = list(set(df['Original Report Tab Name'].tolist()))

    index_dict = {}
    for df_site_gsrange_col in df_site_gsrange_col_list:
        for i in range(len(cc_p_report_list)):
            if cc_p_report_list[i] is None:
                continue
            if df_site_gsrange_col in cc_p_report_list[i]:
                index_dict[df_site_gsrange_col] = i
                break
    df['index_goals_sheet'] = df['Original Report Tab Name'].apply(lambda o: index_dict[o])

    df = pd.merge(df, cpuv_goals[['BBR', 'Campaign Name', 'Line Description', 'Base Rate']],
                  how='left', left_on='index_goals_sheet', right_index=True)
    df = df.drop('index_goals_sheet', axis=1)
    df['UV entered'] = 1

    return df

###################################################################
# All1 & Site Goals
###################################################################

def make_all1(cpm, cpuv, temp_fix_das4flat_fee):
    """Return a dataframe of MTD delivery, both CPM and CPUV combined, labeled with Salesforce info.
    This attempts to find the best match for DFP imps in Salesforce. Specifically, even if BBR in the Order name is old, 
    it will try to find the current BBR.
    
    temp_fix_das4flat_fee is from python_path/monthly_setup_yyyy_mm.py
    """    
 
    # Filter dates for cpuv to match cpm
    last_delivery_date = cpm['Date'].max()
    first_date = last_delivery_date.replace(day=1)
    cpuv = cpuv[(cpuv['Date'] >= first_date) & (cpuv['Date'] <= last_delivery_date)]

    mo = last_delivery_date.month
    year = last_delivery_date.year
    das_month = str(mo) + '/' + str(year)
    das = make_das(use_scheduled_units=False, export=False)
    if temp_fix_das4flat_fee is not None:
        das = temp_fix_das4flat_fee(das)
    das_thismonth = das_filtered(das, das_month).rename(columns={'BBR': '(DAS)BBR #', 
                                                                 'Line Description': 'DAS Line Item Name'})

    ###########################################################
    # Add Brand from BBR
    ###########################################################

    cpm = bbr2brand(cpm, '(Order)BBR #', das)
    cpuv = cpuv.rename(columns={'BBR': '(Order)BBR #'})
    cpuv = bbr2brand(cpuv, '(Order)BBR #', das)

    ###########################################################
    # Add Price Calculation Type ONLY FOR actual CPUV/CPM data
    ###########################################################

    cpm.loc[cpm['Imp Type'] == 'CPM', 'Price Calculation Type'] = 'CPM'
    if len(cpuv) > 0:
        cpuv.loc[cpuv['UV entered'] > 0, 'Price Calculation Type'] = 'CPUV'

    ###########################################################
    # Combine CPUV and CPM
    ###########################################################

    cpm = cpm.rename(columns={'Total impressions': 'Impressions/UVs',
                              'Total clicks': 'Clicks'})
    cpuv = cpuv.rename(columns={'UVs': 'Impressions/UVs', 
                                'Line Description': 'DAS Line Item Name',
                                'Base Rate': 'Rate ($)'})
    all1 = pd.concat([cpm, cpuv])
    del cpm

    ###########################################################
    # Add Match in DAS
    ###########################################################

    # Add count of (Brand, DAS Line Item Name) in Salesforce
    das_thismonth_1 = das_thismonth[['Brand', 'DAS Line Item Name']]
    brand_lin_count = das_thismonth_1.groupby(['Brand', 'DAS Line Item Name']).size().reset_index()
    brand_lin_count = brand_lin_count.rename(columns={0: 'Multiple (Brand, Line item Name) in DAS'})
    all1 = pd.merge(all1, brand_lin_count, how='left', on=['Brand', 'DAS Line Item Name'])

    # Add Salesforce BBR via (Brand, DAS Line Item Name)
    das_thismonth_2 = das_thismonth[['(DAS)BBR #', 'Brand', 'DAS Line Item Name']]
    deduped_brand_lin4bbr = das_thismonth_2.drop_duplicates(['Brand', 'DAS Line Item Name'], keep=False)
    all1 = pd.merge(all1, deduped_brand_lin4bbr, how='left', on=['Brand', 'DAS Line Item Name'])

    all1.loc[all1['Multiple (Brand, Line item Name) in DAS'] > 1, '(DAS)BBR #'] = \
        all1.loc[all1['Multiple (Brand, Line item Name) in DAS'] > 1, '(Order)BBR #']

    # Indicate 1 for having a match with Salesforce via (BBR, Brand, Line Description, Type)
    das_thismonth_3 = das_thismonth[['(DAS)BBR #', 'Brand', 'DAS Line Item Name',
                                     'Price Calculation Type', 'Base Rate']].drop_duplicates()
    das_thismonth_3['Match in DAS'] = 1
    all1 = pd.merge(all1, das_thismonth_3, how='left',
                    on=['(DAS)BBR #', 'Brand', 'DAS Line Item Name', 'Price Calculation Type'])

    """
    def update_das_bbr(row):
        if row['Multiple (Brand, Line item Name) in DAS'] > 1:
            return row['(Order)BBR #']
        return row['(DAS)BBR #']
    
    def update_match_in_das(row):
        if ((row['Price Calculation Type'] == 'CPUV') | (row['Price Calculation Type'] == 'CPM')) & (row['Match in DAS'] != 1):
            return 0
        return row['Match in DAS']

    def update_base_rate(row):
        output = row['Base Rate']        
        if row['Match in DAS'] == 0:
            output = row['Rate ($)']
        if output is None:
            output = 0
        return output
     
    #all1['(DAS)BBR #'] = all1.apply(lambda row: update_das_bbr(row), axis=1)
    #all1['Match in DAS'] = all1.apply(lambda row: update_match_in_das(row), axis=1)
    #all1['Base Rate'] = all1.apply(lambda row: update_base_rate(row), axis=1)
    """

    all1.loc[((all1['Price Calculation Type'] == 'CPUV') | (all1['Price Calculation Type'] == 'CPM')) &
             (all1['Match in DAS'] != 1), 'Match in DAS'] = 0

    all1.loc[all1['Match in DAS'] == 0, 'Base Rate'] = all1.loc[all1['Match in DAS'] == 0, 'Rate ($)']
    all1.loc[pd.isnull(all1['Base Rate']), 'Base Rate'] = 0

    """
    # Split, save, load, and combine (MemoryError workaround)
    def temp_op(df):
        df['(DAS)BBR #'] = df.apply(lambda row: update_das_bbr(row), axis=1)
        df['Match in DAS'] = df.apply(lambda row: update_match_in_das(row), axis=1)
        df['Base Rate'] = df.apply(lambda row: update_base_rate(row), axis=1)
        return df
    
    # Save 1 MM rows to a pickle at a time (prob. unnecessary with more memory)
    len_all1 = len(all1)
    n_mini_all1 = int(len_all1 / 1000000)  
    
    for i in range(n_mini_all1 + 1):
        df = all1[i*1000000: (i+1)*1000000]
        temp_op(df)
        with open('temp_df_' + str(i), 'wb') as f:
            pickle.dump(df, f)
    
    # Create a new dataframe
    col_all1 = all1.columns.tolist()
    del all1
    all1 = pd.DataFrame(index=[i for i in range(len_all1)], columns=col_all1)
    
    count = 0
    for i in range(n_mini_all1 + 1):
        with open('temp_df_' + str(i), 'rb') as f:
            df =  pickle.load(f)
        all1.iloc[count: count+len(df)] = df        
        count += len(df)        
    """

    return all1

def get_site_goals(mo_year, pas_sheet, cpuv_goals_sheet, ls_correct_rate_dict, 
                   drugs_correct_rate_list, temp_fix_das4flat_fee):
    """Return a dataframe of goals at site level, both CPM and CPUV combined.
    Also include MTD discrepancy (from PAS) and Site Rate (what we pay to site).

    ls_correct_rate_dict, drugs_correct_rate_list, and temp_fix_das4flat_fee
    are from python_path/monthly_setup_yyyy_mm.py
    """

    das_month = str(mo_year[0]) + '/' + str(mo_year[1])
    das = make_das(use_scheduled_units=False, export=True)
    das = temp_fix_das4flat_fee(das)

    pas = get_pas(mo_year[1], pas_sheet)
    cpuv_goals = get_cpuv_goals(mo_year[1], cpuv_goals_sheet)

    das_thismonth = das_filtered(das, das_month)

    ###################################################################
    # PAS goals and Disc
    ###################################################################

    pas_relable_sites = {'Drugs': 'Drugs.com', 'MNT': 'Medical News Today', 'BCO': 'Breastcancer.org'}
    pas = pas.rename(columns=pas_relable_sites)

    das_1 = das_thismonth[['BBR', 'Campaign Name', 'Brand']].drop_duplicates()
    pas = pd.merge(pas, das_1, how='left', on='Campaign Name')

    pas_headers = pas.columns.tolist()
    pas_sites = pas_headers[pas_headers.index('Drugs.com'): pas_headers.index('HL')+1]

    pas_formatted = pd.DataFrame()

    for site in pas_sites:
        if site == 'Drugs.com':
            pas_per_site = pas[['BBR', 'Brand', 'Line Description', 'MTD Disc', site]].rename(columns={site: 'Site Goal'})
        else:
            pas_per_site = pas[['BBR', 'Brand', 'Line Description', 'Overall MTD Disc', site]].rename(columns={site: 'Site Goal', 'Overall MTD Disc': 'MTD Disc'})
        pas_per_site = pas_per_site[[((pd.notnull(goal)) & (not isinstance(goal, str))) for goal in pas_per_site['Site Goal']]]
        pas_per_site['Site'] = site
        pas_formatted = pas_formatted.append(pas_per_site)

    pas_formatted = pas_formatted.rename(columns={'Line Description': 'DAS Line Item Name'})

    ###################################################################
    # CPUV goals
    ###################################################################

    das_2 = das_thismonth[['Campaign Name', 'Brand']].drop_duplicates()
    cpuv_col_site_dict = {'HL Goal': 'HL',
                          'Drugs Goal': 'Drugs.com',
                          'GoodRx Goal': 'GoodRx',
                          'MNT Goal': 'Medical News Today',
                          'BCO Goal': 'Breastcancer.org',
                          'LS Goal': 'Livestrong',  # Ended in Dec 2017
                          'EmpowHer Goal': 'EmpowHer'}  # Ended in Dec 2017
    cpuv_goals = pd.merge(cpuv_goals, das_2, how='left', on='Campaign Name')

    cpuv_goals_formatted = pd.DataFrame()

    for col in cpuv_col_site_dict:
        if col not in cpuv_goals.columns.tolist():
            continue

        cpuv_goals_per_site = cpuv_goals[['BBR', 'Brand', 'Line Description', col, 'Report Tab Name']].rename(columns={col: 'Site Goal'})
        if cpuv_col_site_dict[col] == 'HL':
            cpuv_goals_per_site.loc[pd.isnull(cpuv_goals_per_site['Site Goal']), 'Site Goal'] = 0
        else:
            cpuv_goals_per_site = cpuv_goals_per_site[cpuv_goals_per_site['Site Goal'] > 0]
        cpuv_goals_per_site['Site'] = cpuv_col_site_dict[col]
        cpuv_goals_formatted = cpuv_goals_formatted.append(cpuv_goals_per_site)

    cpuv_goals_formatted = cpuv_goals_formatted.rename(columns={'Line Description': 'DAS Line Item Name'})

    ###################################################################
    # Combine the two
    # Add goals not in PAS or CPUV Goals Sheet as HL goal
    # Should be just Not Live
    ###################################################################

    goals = pd.concat([pas_formatted, cpuv_goals_formatted])

    in_goals = goals[['BBR', 'Brand', 'DAS Line Item Name']].drop_duplicates()
    in_goals['In Goals'] = 'Y'

    das_3 = das_thismonth[['BBR', 'Brand', 'Line Description', das_month]].rename(columns={'Line Description': 'DAS Line Item Name', das_month: 'Site Goal'})
    das_3['Site'] = 'HL'

    not_in_goals = pd.merge(das_3, in_goals, how='left', on=['BBR', 'Brand', 'DAS Line Item Name'])
    not_in_goals = not_in_goals[not_in_goals['In Goals'] != 'Y']
    not_in_goals['Not in PAS or CPUV Goals'] = 'Y'

    goals = pd.concat([goals, not_in_goals])
    goals = goals.drop('In Goals', axis=1)

    ###################################################################
    # For non-Drugs HW partners, remove MTD Disc 5% or less
    ###################################################################

    goals.loc[(goals['Site'] != 'HL') & (goals['Site'] != 'Drugs.com') & (goals['MTD Disc'] <= 0.05), 'MTD Disc'] = 0.0

    ###################################################################
    # Add Flight Type, Base Rate, Baked-In Production Rate,
    # Type, Status, and End Date
    ###################################################################

    das_4 = das_thismonth[['BBR', 'Brand', 'Line Description', 'Flight Type', 'Base Rate', 'Baked-In Production Rate', 'Price Calculation Type', 'Stage', 'End Date']].rename(columns={'Line Description': 'DAS Line Item Name'})
    goals = pd.merge(goals, das_4, how='left', on=['BBR', 'Brand', 'DAS Line Item Name'])

    ###################################################################
    # Add Non-standard Site Rate
    ###################################################################

    goals['Non-standard Site Rate'] = ''

    ## LS Minimum rate by condition (CPUV)
    for tab_name in ls_correct_rate_dict:
        rate = ls_correct_rate_dict[tab_name]
        goals.loc[(goals['Site'] == 'Livestrong') & (goals['Report Tab Name'] == tab_name),
                  'Non-standard Site Rate'] = rate

    ## Drugs not 60% CPUV Microsite or CPM
    for bbr, brand, ld, rate in drugs_correct_rate_list:
        goals.loc[(goals['Site'] == 'Drugs.com') &
                  (goals['BBR'] == bbr) &
                  (goals['Brand'] == brand) &
                  (goals['DAS Line Item Name'] == ld),
                  'Non-standard Site Rate'] = rate

    ## Drugs CPUV CC 30 cents for 2017, 40 cents for 2018
    drugs_cc_cpuv = 0.4
    if mo_year[0] == 2017:
        drugs_cc_cpuv = 0.3
    
    goals.loc[(goals['Price Calculation Type'] == 'CPUV') &
              (goals['DAS Line Item Name'].str.contains('Competitive Conquesting')) &
              (goals['Site'] == 'Drugs.com'), 'Non-standard Site Rate'] = drugs_cc_cpuv

    ## Patient Info
    #goals.loc[goals['Site'] == 'Patient Info', 'Non-standard Site Rate'] = 10.0

    ###################################################################
    # Add RevShare and Site Rate
    ###################################################################

    revshare_dict = get_revshare_dict()
    goals['RevShare'] = [revshare_dict[site] for site in goals['Site']]

    # Add Site Rate
    goals['Site Rate'] = goals['Base Rate'] * goals['RevShare']
    goals.loc[goals['Non-standard Site Rate'] != '', 'Site Rate'] = goals.loc[goals['Non-standard Site Rate'] != '', 'Non-standard Site Rate']

    ###################################################################
    # Add Gross Revenue Site (net to partner) Revenue
    ###################################################################

    goals['IO Site Revenue'] = 0
    goals.loc[goals['Price Calculation Type'] == 'CPM', 'IO Site Revenue'] = goals.loc[goals['Price Calculation Type'] == 'CPM'].apply(lambda row: row['Site Goal'] / 1000 * row['Site Rate'], axis=1)
    goals.loc[goals['Price Calculation Type'] == 'CPUV', 'IO Site Revenue'] = goals.loc[goals['Price Calculation Type'] == 'CPUV'].apply(lambda row: row['Site Goal'] * row['Site Rate'], axis=1)

    goals['IO Gross Revenue'] = 0
    goals.loc[goals['Price Calculation Type'] == 'CPM', 'IO Gross Revenue'] = goals.loc[goals['Price Calculation Type'] == 'CPM'].apply(lambda row: row['Site Goal'] / 1000 * row['Base Rate'], axis=1)
    goals.loc[goals['Price Calculation Type'] == 'CPUV', 'IO Gross Revenue'] = goals.loc[goals['Price Calculation Type'] == 'CPUV'].apply(lambda row: row['Site Goal'] * row['Base Rate'], axis=1)

    ###################################################################
    # Clean up
    ###################################################################

    goals.loc[pd.isnull(goals['MTD Disc']), 'MTD Disc'] = 0
    goals = goals[np.invert((goals['Site'] != 'HL') & (goals['Site Goal'] == 0))]

    return goals

