from path2pickles import *
from NEW_helpers import *

import pandas as pd
import numpy as np
import re

from datetime import timedelta
import openpyxl as opx

import os
import io
import pickle
from googleapiclient.http import MediaIoBaseDownload

pd.options.mode.chained_assignment = None  # default='warn'

###################################################################
# Helpers
###################################################################

def cap_delivery(delivery, cap, delivery_col_name):
    original = delivery[delivery_col_name].tolist()
    adjusted = []
    total = 0
    hit_cap = False
    for i in range(len(original)):
        if hit_cap:
            adjusted.append(0)
            continue
        total += original[i]
        if total <= cap:
            adjusted.append(original[i])
            if total == cap:
                hit_cap = True
        else:
            adjusted.append(original[i] - (total - cap))
            hit_cap = True
    delivery['Capped ' + delivery_col_name] = adjusted
    return delivery

def add_year_mo(df, date_col):
    df['year/mo'] = [str(d.year) + '/' + str(d.month).zfill(2) for d in df[date_col]]

def add_erate(df, output_col, type_col, rev_col, delivery_col):
    def calculate_erate(row):
        if row[delivery_col] == 0:
            return 0

        price_type = row[type_col]
        if price_type == 'CPM':
            return row[rev_col] / row[delivery_col] * 1000.0
        elif price_type == 'CPUV':
            return row[rev_col] / row[delivery_col]
        else:
            return 0

    df[output_col] = df.apply(lambda row: calculate_erate(row), axis=1)
    df.loc[pd.isnull(df[output_col]), output_col] = 0

def add_margin(df, rev_col, exp_col, site_col):
    def calculate_margin(row):
        if row[rev_col] == 0:
            if row[site_col] in ['HL', 'Medical News Today']:
                return 1
            else:
                return 0
        return (row[rev_col] - row[exp_col]) / row[rev_col]

    df['Margin'] = df.apply(lambda row: calculate_margin(row), axis=1)

def mtd_delivery_rev(df, date_col, delivery_col, rev_col):
    df = df[[date_col, delivery_col, rev_col]].sort_values(date_col)

    delivery = df[delivery_col].values.tolist()
    mtd_delivery = []
    total_delivery = 0
    for i in range(len(delivery)):
        total_delivery += delivery[i]
        mtd_delivery.append(total_delivery)

    rev = df[rev_col].values.tolist()
    mtd_rev = []
    total_rev = 0
    for i in range(len(rev)):
        total_rev += rev[i]
        mtd_rev.append(total_rev)

    df['MTD ' + delivery_col] = mtd_delivery
    df['MTD ' + rev_col] = mtd_rev

    return df

def fill_in_cc_uvs(all1_or_daily_sr, delivery_col):
    
    delivery = all1_or_daily_sr.copy()

    till_date = delivery[delivery['Price Calculation Type'] == 'CPM']['Date'].max()

    for site in ['Drugs.com', 'GoodRx']:
        df = delivery[(delivery['Site'] == site) &
                      (delivery['Price Calculation Type'] == 'CPUV') &
                      (delivery['DAS Line Item Name'].str.contains('Competitive Conquesting'))]

        daily = df[['Date', delivery_col]].groupby('Date').sum().reset_index()
        daily = daily[daily[delivery_col] > 0]
        if len(daily) == 0:
            continue
        copy_date = daily['Date'].max()
        
        data2copy = df[(df['Site'] == site) & (df['Date'] == copy_date)]
        for n in range(till_date.day - copy_date.day):
            new_date = copy_date + timedelta(days=n + 1)
            data2copy['Date'] = new_date
            df = df[np.invert((df['Site'] == site) & (df['Date'] == new_date))]
            df = pd.concat([df, data2copy])

        delivery = delivery[np.invert((delivery['Site'] == site) &
                                      (delivery['Price Calculation Type'] == 'CPUV') &
                                      (delivery['DAS Line Item Name'].str.contains('Competitive Conquesting')))]
        delivery = pd.concat([delivery, df])

    return delivery

def get_site_group(site):
    if site == 'HL':
        return 'HL'
    if site == 'Medical News Today':
        return 'MNT'
    return 'HW'

###################################################################
# All1 grouped
###################################################################

def get_grouped_delivery(all1, site_goals, groupby_col, clicks=False):
    
    # Delivery
    df = all1[(all1['Price Calculation Type'] == 'CPM') | (all1['Price Calculation Type'] == 'CPUV')]
    df = df.rename(columns={'(DAS)BBR #': 'BBR', 'Impressions/UVs': 'Delivered'})
    df = df[pd.notnull(df['Delivered']) & (df['Delivered'] > 0)]
    if clicks:
        df = df[groupby_col + ['Delivered', 'Clicks']].groupby(groupby_col).sum().reset_index()
    else:
        df = df[groupby_col + ['Delivered']].groupby(groupby_col).sum().reset_index()
    
    # MTD discrepancy
    if 'Site' in groupby_col:
        join_col = ['BBR', 'Brand', 'DAS Line Item Name', 'Site']
        mini_site_goals = site_goals[join_col + ['MTD Disc']]
    else:
        join_col = ['BBR', 'Brand', 'DAS Line Item Name']
        mini_site_goals = site_goals[site_goals['Site'] == 'HL'][join_col + ['MTD Disc']]
    df = pd.merge(df, mini_site_goals, how='left', on=join_col)
    
    # Estimated 3rd party imps
    df.loc[pd.isnull(df['MTD Disc']), 'MTD Disc'] = 0
    df['Adjusted w/ Discrepancy'] = df['Delivered'] * (1 - df['MTD Disc'])
    df['Adjusted w/ Discrepancy'] = [round(awd, 0) for awd in df['Adjusted w/ Discrepancy']]

    return df

def get_mtd_per_pl_delivery(all1, site_goals, clicks=False):
    
    return get_grouped_delivery(all1, site_goals, ['BBR', 'Brand', 'DAS Line Item Name'], clicks)

def get_mtd_per_pl_st_delivery(all1, site_goals, clicks=False):
    
    return get_grouped_delivery(all1, site_goals, ['BBR', 'Brand', 'DAS Line Item Name', 'Site'], clicks)

def get_daily_per_pl_delivery(all1, site_goals, clicks=False):
    
    return get_grouped_delivery(all1, site_goals, ['BBR', 'Brand', 'DAS Line Item Name', 'Date'], clicks)

def get_daily_per_pl_st_delivery(all1, site_goals, clicks=False):

    return get_grouped_delivery(all1, site_goals, ['BBR', 'Brand', 'DAS Line Item Name', 'Site', 'Date'], clicks)


###################################################################
# Add billable
###################################################################

def das_multimonth_bill_up2_col(das, year, mo, quarter=False):
    das = das.copy()
    das_header = das.columns.tolist()
    month_list = []
    for col in das_header:
        if re.search('[0-9]+/[0-9]{4}', col):
            month_list.append(col)

    months2add = []
    if not quarter:
        for month in month_list:
            (mo_, year_) = month.split('/')
            mo_ = int(mo_)
            year_ = int(year_)
            if year_ < year:
                continue
            elif year_ > year:
                months2add.append(month)
            elif mo_ >= mo:
                months2add.append(month)

        for month in months2add:
            das[month].fillna(0, inplace=True)

        das['Multi-Month Bill Up To'] = das.apply(lambda row: round(sum((0 if isinstance(row[month], str) else row[month]) for month in months2add), 0), axis=1)
        das.loc[(das['Flight Type'] == 'Monthly') & (das['Billing Details'] == 'N/A'), 'Multi-Month Bill Up To'] = ''

        return das['Multi-Month Bill Up To']

    else:
        num_mo_left_in_quarter = mo % 3
        months2add.append('/'.join([str(mo), str(year)]))
        if num_mo_left_in_quarter >= 1:
            months2add.append('/'.join([str(mo + 1), str(year)]))
        if num_mo_left_in_quarter == 1:
            months2add.append('/'.join([str(mo + 2), str(year)]))

        for month in months2add:
            das[month].fillna(0, inplace=True)

        das['Quarterly Bill Up To'] = das.apply(lambda row: round(sum((0 if isinstance(row[month], str) else row[month]) for month in months2add), 0), axis=1)
        das.loc[das['Billing Details'] != 'Bill on actual up to quarterly line total', 'Quarterly Bill Up To'] = ''

        return das['Quarterly Bill Up To']

def das_max_billable_col(das, year, mo):
    das = das.copy()
    das['Multi-Month Bill Up To'] = das_multimonth_bill_up2_col(das, year, mo)
    month = str(mo) + '/' + str(year)

    def get_max_billable(row):
        if row['Price Calculation Type'] == 'Flat-fee':
            return row[month]
        if row['Flight Type'] == 'Monthly':
            return row[month]
        plus10per = round(row[month] * 1.1, 0)
        return min(plus10per, row['Multi-Month Bill Up To'])

    das['Max Billable'] = das.apply(lambda row: get_max_billable(row), axis=1)

    return das['Max Billable']

def add_billable_per_pl(per_pl, year, mo):
    # Add per_pl['Billable']

    das = make_das(use_scheduled_units=False, export=False)
    das = das[das[str(mo) + '/' + str(year)] > 0]
    das['Max Billable'] = das_max_billable_col(das, year, mo)
    das = das.rename(columns={'Line Description': 'DAS Line Item Name'})

    per_pl_col = per_pl.columns.tolist()
    join_on = ['BBR', 'Brand', 'DAS Line Item Name']
    per_pl = pd.merge(per_pl, das, how='left', on=join_on)
    
    per_pl['Billable'] = per_pl[['Adjusted w/ Discrepancy', 'Max Billable']].min(axis=1)

    return per_pl[per_pl_col + ['Billable']]

def add_billable_per_pl_st(per_pl_st, per_pl, site_goals):
    # Loops through per_pl to add per_pl_st['Billable']

    # Add goal to per_pl_st
    per_pl_st_col = per_pl_st.columns.tolist()
    join_on = ['BBR', 'Brand', 'DAS Line Item Name', 'Site']
    per_pl_st = pd.merge(per_pl_st, site_goals[join_on + ['Site Goal', 'Price Calculation Type']], how='left', on=join_on)

    per_pl_st['Billable'] = 0
    lst = per_pl[['BBR', 'Brand', 'DAS Line Item Name', 'Billable']].values.tolist()
    for bbr, brand, lin, billable in lst:
        df = per_pl_st[(per_pl_st['BBR'] == bbr) & 
                       (per_pl_st['Brand'] == brand) & 
                       (per_pl_st['DAS Line Item Name'] == lin)]
        ptype = df['Price Calculation Type'].values.tolist()[0]

        # Dict of {site1: delivery1, site2: delivery2, ...}
        site2deliv = pd.Series(df['Adjusted w/ Discrepancy'].values, index=df['Site']).to_dict()
        site2goal = pd.Series(df['Site Goal'].values, index=df['Site']).to_dict()
        site2bill = {}

        if sum(site2deliv.values()) <= billable:  # All delivery is billable
            site2bill = site2deliv

        elif len(site2deliv) == 1:  # Only one site
            for site in site2deliv:
                site2bill[site] = billable

        else:
            # 1. Cap partners at goals, except for Drugs CPUV Non-CC
            for site in site2deliv:
                if site in ['HL', 'Medical News Today']:
                    continue
                if (site == 'Drugs.com') and (ptype == 'CPUV') and ('competitive conquesting' not in lin.lower()):
                    site2bill[site] = min(site2deliv[site], billable)
                else:
                    site2bill[site] = min(site2deliv[site], site2goal[site])

            left = billable - sum(site2bill.values())

            # 2. Max MNT
            if 'Medical News Today' in site2deliv:
                site2bill['Medical News Today'] = min(site2deliv['Medical News Today'], left)
            left = billable - sum(site2bill.values())

            # 3. Max HL
            if 'HL' in site2deliv:
                site2bill['HL'] = min(site2deliv['HL'], left)
            left = billable - sum(site2bill.values())

            # 4. If more billable is left, allocate to lower revshare site first
            if left > 0:
                if (ptype == 'CPUV') and ('competitive conquesting' in lin.lower()):
                    site_order = ['Drugs.com', 'GoodRx', 'Breastcancer.org']
                else:
                    site_order = ['GoodRx', 'Breastcancer.org', 'Drugs.com']

                for site in site_order: 
                    if site in site2deliv:
                        site2bill[site] = min(site2deliv[site], site2goal[site] + left)
                        left = billable - sum(site2bill.values())

        # Dump into Billable
        for site, bill in site2bill.items():
            per_pl_st.loc[(per_pl_st['BBR'] == bbr) &
                          (per_pl_st['Brand'] == brand) &
                          (per_pl_st['DAS Line Item Name'] == lin) &
                          (per_pl_st['Site'] == site)
                          , 'Billable'] = bill

    return per_pl_st[per_pl_st_col + ['Billable']]

def add_billable_per_st_day(per_st_day, per_pl_st):
    # Loops through per_pl_st to add per_st_day['Billable']

    to_concat = []
    lst = per_pl_st[['BBR', 'Brand', 'DAS Line Item Name', 'Site', 'Billable']].values.tolist()
    for bbr, brand, lin, site, billable in lst:
        df = per_st_day[(per_st_day['BBR'] == bbr) & 
                        (per_st_day['Brand'] == brand) & 
                        (per_st_day['DAS Line Item Name'] == lin) &
                        (per_st_day['Site'] == site)]

        df = df.sort_values('Date')  # Sort by date
        df_plus_billable = cap_delivery(df, billable, 'Adjusted w/ Discrepancy') 
        to_concat.append(df_plus_billable)

    per_st_day = pd.concat(to_concat)
    per_st_day = per_st_day.rename(columns={'Capped Adjusted w/ Discrepancy': 'Billable'})

    return per_st_day

###################################################################
# Daily Site Report
###################################################################

def get_daily_site_report(all1, site_goals):
   
    ###################################################################
    # 0. Prep
    ###################################################################

    last_delivery_date = all1[all1['Price Calculation Type'] == 'CPM']['Date'].max()
    mo = last_delivery_date.month
    year = last_delivery_date.year
    das_month = str(mo) + '/' + str(year)

    das = make_das(use_scheduled_units=False, export=False)
    das_thismonth = das[(das[das_month] > 0) & (das['Campaign Manager'] != 'SEM')].rename(
        columns={'Line Description': 'DAS Line Item Name',
                 'Price Calculation Type': 'DAS Price Calculation Type'})

    header_pl = ['BBR', 'Brand', 'DAS Line Item Name']    
    header_st = ['BBR', 'Brand', 'DAS Line Item Name', 'Site']    

    ###################################################################
    # 1. Daily delivery & billable per placement & site
    ###################################################################

    # Grouped delivery
    per_pl = get_mtd_per_pl_delivery(all1, site_goals)
    per_pl_st = get_mtd_per_pl_st_delivery(all1, site_goals)
    per_st_day = get_daily_per_pl_st_delivery(all1, site_goals, clicks=True)

    # Add billable
    per_pl = add_billable_per_pl(per_pl, year, mo)  # per_pl['Billable']
    per_pl_st = add_billable_per_pl_st(per_pl_st, per_pl, site_goals)  # per_pl_st['Billable']
    per_st_day = add_billable_per_st_day(per_st_day, per_pl_st)  # per_st_day['Billable']

    ###################################################################
    # 2. Revenue and Expense
    ###################################################################

    per_st_day = pd.merge(per_st_day, site_goals[
        ['BBR', 'Brand', 'DAS Line Item Name', 'Site', 'Base Rate', 'Baked-In Production Rate', 'Site Rate',
         'Price Calculation Type']], how='left', on=header_st)

    def calculate_amount(row, rate_col, include_prod_fee):
        price_type = row['Price Calculation Type']
        if price_type == 'CPM':
            return row['Billable'] / 1000.0 * row[rate_col]
        elif price_type == 'CPUV':
            if include_prod_fee:
                return row['Billable'] * (row[rate_col] + row['Baked-In Production Rate'])
            else:
                return row['Billable'] * row[rate_col]
        else:
            return 0

    per_st_day['Revenue'] = per_st_day.apply(lambda row: calculate_amount(row, 'Base Rate', True), axis=1)
    per_st_day['Expense'] = per_st_day.apply(lambda row: calculate_amount(row, 'Site Rate', False), axis=1)

    per_st_day['Prod. Fee'] = per_st_day['Billable'] * per_st_day['Baked-In Production Rate']
    per_st_day.loc[(per_st_day['Site'] == 'HL') | (per_st_day['Site'] == 'Medical News Today'), 'Expense'] = 0
    per_st_day['Expense + Prod. Fee'] = per_st_day['Expense'] + per_st_day['Prod. Fee']

    ###################################################################
    # 3. Flat-fee
    ###################################################################

    def daily_flatfee(das_month):

        das = make_das(use_scheduled_units=False, export=False)
        flat_das = das[(das[das_month] > 0) &
                       (das['Price Calculation Type'] == 'Flat-fee') &
                       (das['Campaign Manager'] != 'SEM') &
                       (das['Campaign Manager'] != 'N/A')]

        mo, year = [int(i) for i in das_month.split('/')]
        start_date, end_date = start_end_month(date(year, mo, 1))

        flat_das['Campaign Start Date'] = [start_date if sd <= start_date else sd for sd in flat_das['Start Date']]
        flat_das['Campaign End Date'] = [end_date if ed >= end_date else ed for ed in flat_das['End Date']]

        flat_das['Days'] = flat_das.apply(lambda row: (row['Campaign End Date'] - row['Campaign Start Date']).days + 1, axis=1)
        flat_das['Rev Per Day'] = flat_das['Sales Price'] * flat_das[das_month] / flat_das['Days']

        flat_df = pd.DataFrame()
        for i in range(len(flat_das)):
            flat_line = flat_das.iloc[i]
            list_days = []
            temp_date = flat_line['Campaign Start Date']
            while temp_date <= flat_line['Campaign End Date']:
                list_days.append(temp_date)
                temp_date += timedelta(days=1)
            to_add = pd.DataFrame({'Date': list_days})
            for col in ['Price Calculation Type', 'BBR', 'Brand', 'Line Description']:
                to_add[col] = flat_line[col]
            to_add['Site'] = 'HL'
            to_add['Revenue'] = flat_line['Rev Per Day']
            flat_df = pd.concat([flat_df, to_add])

        return flat_df

    mtd_flat = daily_flatfee(das_month).rename(columns={'Line Description': 'DAS Line Item Name'})
    mtd_flat = mtd_flat[mtd_flat['Date'] <= last_delivery_date]
    per_st_day = pd.concat([per_st_day, mtd_flat])

    for col in ['Delivered', 'MTD Disc', 'Adjusted w/ Discrepancy', 'Billable', 'Base Rate', 'Baked-In Production Rate',
                'Site Rate', 'Expense', 'Prod. Fee', 'Expense + Prod. Fee']:
        per_st_day.loc[per_st_day['Price Calculation Type'] == 'Flat-fee', col] = 0

    price_flight_type = das_thismonth[header_pl + ['DAS Price Calculation Type', 'Flight Type']]
    per_st_day = pd.merge(per_st_day, price_flight_type, how='left', on=header_pl)
    per_st_day.loc[pd.isnull(per_st_day['DAS Price Calculation Type']), 'DAS Price Calculation Type'] = 'No Goal'

    ###################################################################
    # 4. Delivery with no goal
    ###################################################################

    per_st_day.loc[pd.isnull(per_st_day['Price Calculation Type']), 'Price Calculation Type'] = 'No Goal'

    for col in ['MTD Disc', 'Billable', 'Base Rate', 'Baked-In Production Rate',
                'Site Rate', 'Revenue', 'Expense', 'Prod. Fee', 'Expense + Prod. Fee']:
        per_st_day.loc[per_st_day['Price Calculation Type'] == 'No Goal', col] = 0

    ###################################################################
    # 5. Site Group
    ###################################################################

    per_st_day['Site Group'] = per_st_day['Site'].apply(get_site_group)

    ###################################################################
    # 6. Clean up
    ###################################################################

    per_st_day = per_st_day[['DAS Price Calculation Type', 'Price Calculation Type',
                             'BBR', 'Brand', 'DAS Line Item Name', 'Site', 'Date', 'Delivered',
                             'MTD Disc', 'Adjusted w/ Discrepancy',
                             'Billable', 'Clicks', 'Revenue', 'Expense', 'Prod. Fee', 'Expense + Prod. Fee',
                             'Base Rate', 'Baked-In Production Rate', 'Site Rate', 'Flight Type',
                             'Site Group']]
    return per_st_day

###################################################################
# Aggregated DAS Revenue, Expense, eCPM/eCPUV on 3 levels
###################################################################

def get_das_aggregated_dict(daily_site_report, add_special_case):

    das_aggregated_dict = {}

    ###################################################################
    # 1. per campaign/placement, site, and date
    ###################################################################

    df = daily_site_report.copy()
    add_year_mo(df, 'Date')
    add_erate(df, 'eCPM/eCPUV', 'Price Calculation Type', 'Revenue', 'Delivered')
    add_margin(df, 'Revenue', 'Expense + Prod. Fee', 'Site')
    df['Special Case'] = ''
    add_special_case(df)

    col = ['Price Calculation Type', 'BBR', 'Brand', 'DAS Line Item Name', 'Site', 'year/mo', 'Date', 
           'Delivered', 'MTD Disc', 'Adjusted w/ Discrepancy', 'Billable', 'Revenue', 
           'Expense + Prod. Fee', 'eCPM/eCPUV', 'Margin', 'Special Case']
    
    col_rename_dict = {'DAS Line Item Name': 'Line Description',
                       'Delivered': 'DFP/GA Delivered',
                       'Adjusted w/ Discrepancy': 'Adjusted w/ Disc',
                       'Billable': 'Billable Delivery',
                       'Expense + Prod. Fee': 'Expense'}
    
    sortby = ['Price Calculation Type', 'Brand', 'BBR', 'Line Description', 'Site', 'Date']
    
    df = df[col].rename(columns=col_rename_dict).sort_values(sortby)

    das_aggregated_dict['per site & placement'] = {'df': df, 'sortby': sortby}

    ###################################################################
    # 2. per site and date
    ###################################################################

    df = daily_site_report.copy()
    groupby_col = ['DAS Price Calculation Type', 'Price Calculation Type', 'Site', 'Date']
    values_col = ['Delivered', 'Revenue', 'Expense + Prod. Fee']
    df = df[groupby_col + values_col].groupby(groupby_col).sum().reset_index()
    
    add_year_mo(df, 'Date')
    add_erate(df, 'eCPM/eCPUV', 'DAS Price Calculation Type', 'Revenue', 'Delivered')
    add_margin(df, 'Revenue', 'Expense + Prod. Fee', 'Site')
    
    mtd = pd.DataFrame()
    dastype_type_site_list = df[['DAS Price Calculation Type', 'Price Calculation Type', 'Site']].drop_duplicates().values.tolist()
    for das_type, type, site in dastype_type_site_list:
        to_add = mtd_delivery_rev(df[(df['DAS Price Calculation Type'] == das_type) &
                                     (df['Price Calculation Type'] == type) &
                                     (df['Site'] == site)], 
                                  'Date', 'Delivered', 'Revenue')
        to_add['DAS Price Calculation Type'] = das_type
        to_add['Price Calculation Type'] = type
        to_add['Site'] = site
        mtd = pd.concat([mtd, to_add.drop(['Delivered', 'Revenue'], axis=1)])

    df = pd.merge(df, mtd, how='left', on=['DAS Price Calculation Type', 'Price Calculation Type', 'Site', 'Date'])
    add_erate(df, 'MTD eCPM/eCPUV', 'DAS Price Calculation Type', 'MTD Revenue', 'MTD Delivered')
    
    col = ['DAS Price Calculation Type', 'Price Calculation Type', 'Site', 'year/mo', 'Date',
           'Delivered', 'Revenue', 'Expense + Prod. Fee', 'eCPM/eCPUV', 'Margin',
           'MTD Delivered', 'MTD Revenue', 'MTD eCPM/eCPUV']
    
    col_rename_dict = {'Delivered': 'DFP/GA Delivered',
                       'Expense + Prod. Fee': 'Expense',
                       'MTD Delivered': 'MTD DFP/GA Delivered'}

    sortby = ['DAS Price Calculation Type', 'Price Calculation Type', 'Site', 'Date']
    
    df = df[col].rename(columns=col_rename_dict).sort_values(sortby)

    das_aggregated_dict['per site'] = {'df': df, 'sortby': sortby}

    ###################################################################
    # 3. by date, CPM & CPUV only
    ###################################################################

    df = daily_site_report.copy()
    df = df[(df['DAS Price Calculation Type'] == 'CPM') | (df['DAS Price Calculation Type'] == 'CPUV')]
    col = ['DAS Price Calculation Type', 'Date', 'Delivered', 'Revenue']
    df = df[col].groupby(['DAS Price Calculation Type', 'Date']).sum().reset_index()
    
    add_year_mo(df, 'Date')
    add_erate(df, 'eCPM/eCPUV', 'DAS Price Calculation Type', 'Revenue', 'Delivered')
    
    mtd = pd.DataFrame()
    for type in ['CPM', 'CPUV']:
        to_add = mtd_delivery_rev(df[df['DAS Price Calculation Type'] == type], 
                                  'Date', 'Delivered', 'Revenue')
        to_add['DAS Price Calculation Type'] = type
        mtd = pd.concat([mtd, to_add.drop(['Delivered', 'Revenue'], axis=1)])
        
    df = pd.merge(df, mtd, how='left', on=['DAS Price Calculation Type', 'Date'])
    add_erate(df, 'MTD eCPM/eCPUV', 'DAS Price Calculation Type', 'MTD Revenue', 'MTD Delivered')
    
    col = ['DAS Price Calculation Type', 'year/mo', 'Date', 'eCPM/eCPUV', 'MTD eCPM/eCPUV']
    col_rename_dict = {'DAS Price Calculation Type': 'Price Calculation Type'}
    sortby = ['Price Calculation Type', 'Date']
    df = df[col].rename(columns=col_rename_dict).sort_values(sortby)

    def extract_type(df, price_type):
        col_rename_dict = {'eCPM/eCPUV': 'e' + price_type,
                           'MTD eCPM/eCPUV': 'MTD e' + price_type}
        return df[df['Price Calculation Type'] == price_type].rename(columns=col_rename_dict)

    cpm = extract_type(df, 'CPM')
    cpuv = extract_type(df, 'CPUV')
    col = ['year/mo', 'Date', 'eCPM', 'MTD eCPM', 'eCPUV', 'MTD eCPUV']
    df = pd.merge(cpm, cpuv, how='outer', on=['year/mo', 'Date'])[col]

    das_aggregated_dict['overview'] = {'df': df, 'sortby': ['Date']}

    return das_aggregated_dict

def up_das_agg2gsheet(das_aggregated_dict):
    
    ####################################################################
    ss_id = '1r4pF5mv4Ic9ZduZJ1Oi2xubNp2-hLE-CrcthglUOVDQ'
    ####################################################################

    dir_name = 'DAS Agg Backup'
    check_and_make_dir(dir_name)

    service = get_gsheet_service()

    for sheet in das_aggregated_dict:

        s_id = gsheet_get_sheet_id_by_name(sheet, ss_id)
        df = das_aggregated_dict[sheet]['df']
        sortby = das_aggregated_dict[sheet]['sortby']

        ####################################################################
        # Grab existing data from sheet, save it as a csv file
        ####################################################################

        response = service.spreadsheets().values().get(
            spreadsheetId=ss_id, range=sheet,
            majorDimension='ROWS', valueRenderOption='UNFORMATTED_VALUE').execute()
        values = response['values']
        header = values.pop(0)
        len_header = len(header)
        for row in values:
            len_row = len(row)
            if len_row < len_header:
                for _ in range(len_header - len_row):
                    row.append('')
        existing = pd.DataFrame(values, columns=header)

        existing.to_csv(dir_name + '/' + sheet + '_' + datetime.now().strftime('%Y%m%d_%Hhr%Mmin%Ssec') + '.csv')

        ####################################################################
        # Replace MTD
        ####################################################################

        print(sheet)

        df['Date'] = pd.to_datetime(df['Date']).dt.date
        existing['Date'] = [(date(1900, 1, 1) + timedelta(days=int(d) - 2)) for d in
                            existing['Date']]  # GoogleSheet date is in the integer form
        adding_from = min(df['Date'])
        to_upload = pd.concat([existing[existing['Date'] < adding_from], df])

        if sheet == 'per site & placement':
            max_date = max(df['Date'])
            thirty_one_days_ago = max_date - timedelta(days=31)
            to_upload = to_upload[(to_upload['Date'] >= thirty_one_days_ago) & (to_upload['Date'] <= max_date)]

        ####################################################################
        # Clean up and sort
        ####################################################################

        to_upload['Date'] = [str(d) for d in to_upload['Date']]  # upload isn't doable with date type
        to_upload = to_upload[header].sort_values(sortby)
        to_upload = to_upload.fillna('')

        ####################################################################
        # Upload
        ####################################################################

        clear_all = [{'updateCells': {'range': {'sheetId': s_id}, 'fields': 'userEnteredValue'}}]
        result = service.spreadsheets().batchUpdate(
            spreadsheetId=ss_id, body={'requests': clear_all}).execute()

        upload_data = [{'range': sheet + '!A:Z', 'majorDimension': 'ROWS',
                        'values': [to_upload.columns.tolist()] + to_upload.values.tolist()}]
        result = service.spreadsheets().values().batchUpdate(
            spreadsheetId=ss_id, body={'valueInputOption': 'USER_ENTERED', 'data': upload_data}).execute()

        ####################################################################
        # Correct Date formatting
        ####################################################################

        date_col_index = to_upload.columns.tolist().index('Date')
        yrmo_col_index = to_upload.columns.tolist().index('year/mo')

        upload_formatting = [{'repeatCell': {'range': {'sheetId': s_id,
                                                       'startRowIndex': 1,
                                                       'endRowIndex': len(to_upload) + 1,
                                                       'startColumnIndex': date_col_index,
                                                       'endColumnIndex': date_col_index + 1},
                                             'cell': {'userEnteredFormat': {'numberFormat': {'type': 'DATE',
                                                                                             'pattern': 'm/d/yyyy'}}},
                                             'fields': 'userEnteredFormat.numberFormat'}},
                             {'repeatCell': {'range': {'sheetId': s_id,
                                                       'startRowIndex': 1,
                                                       'endRowIndex': len(to_upload) + 1,
                                                       'startColumnIndex': yrmo_col_index,
                                                       'endColumnIndex': yrmo_col_index + 1},
                                             'cell': {'userEnteredFormat': {'numberFormat': {'type': 'DATE',
                                                                                             'pattern': 'yyyy/mm'}}},
                                             'fields': 'userEnteredFormat.numberFormat'}}]

        result = service.spreadsheets().batchUpdate(
            spreadsheetId=ss_id, body={'requests': upload_formatting}).execute()
    
    return None

def up_das_agg2gdrive(per_site_pl_dict):

    ################################################
    folder_id = '0B71ox_2Qc7gmRUlQajVxd3A3OVk'
    ################################################

    df = per_site_pl_dict['df']
    sortby = per_site_pl_dict['sortby']

    service = get_gdrive_service()

    ################################################
    # Download the most recent file
    ################################################

    file_id = gdrive_get_most_recent_file_id(folder_id)

    if file_id is not None:
        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            # print("Download %d%%." % int(status.progress() * 100))

        ################################################
        # Save to a csv
        ################################################

        temp_file_name = 'temp_daily_per_placement_site.csv'
        with open(temp_file_name, 'wb') as f:
            f.write(fh.getvalue())

        ################################################
        # Replace MTD
        ################################################

        existing = pd.read_csv(temp_file_name, encoding='utf-8')
        header = existing.columns.tolist()

        existing['Date'] = pd.to_datetime(existing['Date']).dt.date
        adding_from = min(df['Date'])
        to_upload = pd.concat([existing[existing['Date'] < adding_from], df])

        to_upload = to_upload[header].sort_values(sortby)
        os.remove(temp_file_name)

    else:
        to_upload = df.sort_values(sortby)

    ################################################
    # Upload csv
    ################################################

    file_name = 'Daily_Non-DSP_DAS_Aggregated_' + datetime.now().strftime('%Y%m%d_%Hhr%Mmin') + '.csv'
    to_upload.to_csv(file_name, index=False, encoding='utf-8')
    save_in_gdrive(file_name, folder_id, 'text/csv')
    os.remove(file_name)

    return None

###################################################################
# Projection
###################################################################

def get_projection(daily_delivery, delivery_col, groupby_col,
                   date_col, last_delivery_date):

    ###################################################################
    # Prep
    ###################################################################

    mtd = daily_delivery[groupby_col + [delivery_col]]
    mtd = mtd.groupby(groupby_col).sum().reset_index()
    mtd = mtd.rename(columns={delivery_col: 'MTD'})

    ###################################################################
    # Last 7 days' delivery per day
    ###################################################################

    df = daily_delivery[groupby_col + [date_col] + [delivery_col]]
    df = df.groupby(groupby_col + [date_col]).sum().reset_index()

    for i in range(7):
        what_date = last_delivery_date - timedelta(days=(6 - i))
        what_delivery = df[df['Date'] == what_date][groupby_col + [delivery_col]]
        mtd = pd.merge(mtd, what_delivery, how='left', on=groupby_col)
        mtd.loc[pd.isnull(mtd[delivery_col]), delivery_col] = 0
        mtd = mtd.rename(columns={delivery_col: 'Prev_Week_Day' + str(i)})

    ###################################################################
    # Days left
    ###################################################################

    mo = last_delivery_date.month
    year = last_delivery_date.year
    das_month = str(mo) + '/' + str(year)

    das = make_das(False, False)
    das = das[das[das_month] > 0][['BBR', 'Brand', 'Line Description', 'End Date']]
    das = das.rename(columns={'Line Description': 'DAS Line Item Name'})

    mtd = pd.merge(mtd, das, how='left', on=['BBR', 'Brand', 'DAS Line Item Name'])
    mtd = mtd[pd.notnull(mtd['End Date'])]

    end_date = start_end_month(last_delivery_date)[1]
    mtd['End Date'] = [(end_date if (ed > end_date) else ed) for ed in mtd['End Date']]
    mtd['days_left'] = [int((ed - last_delivery_date).days) for ed in mtd['End Date']]
    mtd['days_left'] = [(0 if (dl < 0) else dl) for dl in mtd['days_left']]
    mtd['num_full_week_left'] = mtd['days_left'] // 7
    mtd['num_days_final_week_left'] = mtd['days_left'] % 7

    ###################################################################
    # Copy last 7 days' delivery for the rest of month
    ###################################################################

    def rom_estimate(row):
        output = 0
        output += row['num_full_week_left'] * sum(row['Prev_Week_Day' + str(i)] for i in range(7))
        for i in range(row['num_days_final_week_left']):
            output += row['Prev_Week_Day' + str(i)]
        return output

    mtd['Rest of Month Estimated Delivery'] = mtd.apply(lambda row: rom_estimate(row), axis=1)

    ###################################################################
    # MTD + Rest of Month
    ###################################################################

    mtd['Projected Delivery'] = mtd['MTD'] + mtd['Rest of Month Estimated Delivery']
    mtd = mtd[groupby_col + ['Projected Delivery']]

    return mtd

###################################################################
# Pacing Report
###################################################################

def get_pacing_report_dict(all1, site_goals):

    last_delivery_date = all1[all1['Price Calculation Type'] == 'CPM']['Date'].max()
    start_date, end_date = start_end_month(last_delivery_date)

    mo = last_delivery_date.month
    year = last_delivery_date.year
    das_month = str(mo) + '/' + str(year)

    das = make_das(False, False)
    das_thismonth = das_filtered(das, das_month)

    all1 = fill_in_cc_uvs(all1, 'Impressions/UVs')

    ###################################################################
    # SEM BNL
    ###################################################################

    das_sem_bnl = das[(das['Campaign Manager'] == 'SEM') &
                      (das['Stage'] == 'Booked Not Live') &
                      (das[das_month] > 0)]

    ###################################################################
    # Prep Rollover
    ###################################################################

    rollover = das.copy()
    months = []
    for col in rollover.columns.tolist():
        if re.search('([0-9]+/[0-9]+)', col):
            months.append(re.search('([0-9]+/[0-9]+)', col).group(1))
    rollover['Actual Units'] = rollover.apply(lambda row: sum(row[mo] for mo in months), axis=1)
    rollover['Rollover Units'] = rollover['Total Units'] - rollover['Actual Units']

    def calculate_amount(row):
        price_type = row['Price Calculation Type']
        if price_type == 'CPM':
            return row['Rollover Units'] / 1000 * row['Sales Price']
        if price_type == 'CPUV':
            return row['Rollover Units'] * row['Sales Price']
        return None

    rollover['Rollover Amount'] = rollover.apply(lambda row: calculate_amount(row), axis=1)

    months_this_year = []
    for mo in months:
        if str(year) in mo:
            months_this_year.append(mo)
    rollover['This Year'] = 0
    for mo in months_this_year:
        rollover.loc[rollover[mo] > 0, 'This Year'] = 1

    rollover = rollover[
        ((rollover['Price Calculation Type'] == 'CPM') | (rollover['Price Calculation Type'] == 'CPUV')) &
        (rollover['Start Date'] <= end_date) &
        (rollover['This Year'] == 1) &
        (rollover['Flight Type'] != 'Multi-Month')]

    rollover_1 = rollover[(rollover['End Date'] < start_date) & (rollover['Rollover Units'] > 0)]
    rollover_2 = rollover[(rollover['End Date'] >= start_date) & (rollover['Rollover Units'] != 0)]
    rollover = pd.concat([rollover_1, rollover_2])

    rollover_olis = rollover['OLI'].tolist()
    das_rollover = das[[(oli in rollover_olis) for oli in das['OLI']]]

    ###################################################################
    # All campaigns to be in report
    ###################################################################

    pacing = pd.concat([das_thismonth, das_sem_bnl, das_rollover]).drop_duplicates()
    pacing = pacing.rename(columns={das_month: 'Goal'})

    ###################################################################
    # Rollover
    ###################################################################

    join_on = ['BBR', 'Campaign Name', 'Line Description']
    rollover = rollover[join_on + ['Rollover Units', 'Rollover Amount']]
    pacing = pd.merge(pacing, rollover, how='left', on=join_on)
    for col in ['Rollover Units', 'Rollover Amount']:
        pacing.loc[pd.isnull(pacing[col]), col] = 0
    
    ###################################################################
    # BNL
    ###################################################################

    def add_bnl(row):
        stage = row['Stage']
        price_type = row['Price Calculation Type']
        if stage == 'Booked Not Live':
            if price_type == 'CPM':
                return row['Goal'] / 1000 * row['Sales Price']
            if price_type == 'CPUV':
                return row['Goal'] * row['Sales Price']
        return 0

    pacing['BNL'] = pacing.apply(lambda row: add_bnl(row), axis=1)

    ###################################################################
    # Delivery
    ###################################################################

    delivery = get_mtd_per_pl_delivery(all1, site_goals)
    delivery = delivery.rename(columns={'DAS Line Item Name': 'Line Description'})

    join_on = ['BBR', 'Brand', 'Line Description']
    pacing = pd.merge(pacing, delivery, how='left', on=join_on)
    for col in ['Adjusted w/ Discrepancy', 'MTD Disc', 'Delivered']:
        pacing.loc[pd.isnull(pacing[col]), col] = 0

    ###################################################################
    # Pacing, 2 versions
    ###################################################################

    # Prep for pacing based on daily average
    pacing['Campaign Start Date'] = [start_date if sd <= start_date else sd for sd in pacing['Start Date']]
    pacing['Campaign End Date'] = [end_date if ed >= end_date else ed for ed in pacing['End Date']]
    pacing['Days'] = pacing.apply(lambda row: (row['Campaign End Date'] - row['Campaign Start Date']).days + 1, axis=1)
    pacing['Past Days'] = pacing.apply(lambda row: (last_delivery_date - row['Campaign Start Date']).days + 1, axis=1)
    pacing.loc[pacing['Past Days'] < 0, 'Past Days'] = 0

    def add_need_2b_on_pace(row):
        if row['Campaign End Date'] <= last_delivery_date:
            return row['Goal']
        if row['Days'] == 0:
            return 0
        return int(row['Goal'] / row['Days'] * row['Past Days'])

    pacing['Need 2b On Pace'] = pacing.apply(lambda row: add_need_2b_on_pace(row), axis=1)

    ###################################################################
    # Projections, 2 versions
    ###################################################################

    daily_delivery = get_daily_per_pl_delivery(all1, site_goals)
    projection = get_projection(daily_delivery, delivery_col='Adjusted w/ Discrepancy',
                                groupby_col=['BBR', 'Brand', 'DAS Line Item Name'],
                                date_col='Date', last_delivery_date=last_delivery_date)
    projection = projection.rename(columns={'DAS Line Item Name': 'Line Description', 'Projected Delivery': 'Projected Delivery_7'})
    join_on = ['BBR', 'Brand', 'Line Description']
    pacing = pd.merge(pacing, projection, how='left', on=join_on)
    pacing.loc[pd.isnull(pacing['Projected Delivery_7']), 'Projected Delivery_7'] = 0

    def add_ave_daily_delivery_projection(row):
        if row['Past Days'] == 0:
            return 'Not started yet'
        return row['Adjusted w/ Discrepancy'] / row['Past Days'] * row['Days']

    pacing['Projected Delivery'] = pacing.apply(lambda row: add_ave_daily_delivery_projection(row), axis=1)

    ###################################################################
    # Pacing, 2 versions
    ###################################################################

    # Main
    def add_pacing(row, divident_col, divider_col):
        if row['Campaign End Date'] <= last_delivery_date:
            return 'Ended'
        if row['Past Days'] == 0:
            return 'Not started yet'
        if row[divider_col] == 0:
            return 'No goal or at goal'
        return row[divident_col] / row[divider_col]

    pacing['Pacing'] = pacing.apply(
        lambda row: add_pacing(row, 'Adjusted w/ Discrepancy', 'Need 2b On Pace'), axis=1)

    pacing['Pacing_7'] = pacing.apply(
        lambda row: add_pacing(row, 'Projected Delivery_7', 'Goal'), axis=1)

    ###################################################################
    # RA, 2 versions
    ###################################################################

    def add_ra(row, pacing_col, return_dollar_amount):
        if row['Campaign Manager'] == 'SEM':
            return 0
        if row['Stage'] == 'Booked Not Live':
            return 0
        if isinstance(row[pacing_col], str):
            return 0
        price_type = row['Price Calculation Type']
        if row[pacing_col] < 1.0:
            if price_type == 'CPM':
                if return_dollar_amount:
                    return (1.0 - row[pacing_col]) * row['Goal'] / 1000 * row['Sales Price']
                else:
                    return (1.0 - row[pacing_col]) * row['Goal']
            if price_type == 'CPUV':
                if return_dollar_amount:
                    return (1.0 - row[pacing_col]) * row['Goal'] * row['Sales Price']
                else:
                    return (1.0 - row[pacing_col]) * row['Goal']
        return 0

    pacing['$RA'] = pacing.apply(lambda row: add_ra(row, 'Pacing', True), axis=1)
    pacing['$RA_7'] = pacing.apply(lambda row: add_ra(row, 'Pacing_7', True), axis=1)
    pacing['RA'] = pacing.apply(lambda row: add_ra(row, 'Pacing', False), axis=1)
    pacing['RA_7'] = pacing.apply(lambda row: add_ra(row, 'Pacing_7', False), axis=1)

    ###################################################################
    # Hit goal & UD
    ###################################################################

    pacing['Hit the Goal'] = 0
    pacing.loc[pacing['Adjusted w/ Discrepancy'] >= pacing['Goal'], 'Hit the Goal'] = 1

    def add_ud(row):
        price_type = row['Price Calculation Type']
        if row['Pacing'] == 'Ended':
            if price_type == 'CPM':
                ud = (row['Goal'] - row['Adjusted w/ Discrepancy']) / 1000 * row['Sales Price']
            elif price_type == 'CPUV':
                ud = (row['Goal'] - row['Adjusted w/ Discrepancy']) * row['Sales Price']
            if ud < 0:
                ud = 0
        else:
            ud = 0
        return ud

    pacing['UD'] = pacing.apply(lambda row: add_ud(row), axis=1)

    ###################################################################
    # Clean up
    ###################################################################

    col = ['Stage', 'BBR', 'Campaign Name', 'Line Item Number', 'Line Description',
           'Price Calculation Type', 'Start Date', 'End Date', 'Sales Price', 'Goal', 
           'Hit the Goal', 
           'Projected Delivery', 'RA', '$RA', 'Pacing',
           'Projected Delivery_7', 'RA_7', '$RA_7', 'Pacing_7', 
           'BNL', 'UD', 'Rollover Units', 'Rollover Amount',
           'Account Manager', 'Campaign Manager']
    sortby = ['Campaign Name', 'BBR', 'Line Item Number']

    pacing = pacing[col].sort_values(sortby)
    
    return {'df': pacing, 'start date': start_date, 'end date': last_delivery_date}

def up_pacing2gdrive(pacing_report_dict):

    ###################################################################
    folder_id = '0B71ox_2Qc7gmLW54VlhUeHZ6cGc'
    ###################################################################

    # File name
    sd = pacing_report_dict['start date']
    ed = pacing_report_dict['end date']

    date_range = ''
    date_range += str(sd.month).zfill(2) + str(sd.day).zfill(2) + str(sd.year - 2000)
    date_range += '_'
    date_range += str(ed.month).zfill(2) + str(ed.day).zfill(2) + str(ed.year - 2000)

    file_name = 'pacing_' + date_range + '.xlsx'

    # Create file
    writer = pd.ExcelWriter(file_name)
    pacing_report_dict['df'].to_excel(writer, date_range, index=False)
    writer.save()

    # Upload
    save_in_gdrive(file_name, folder_id, 'application/vnd.ms-excel')
    os.remove(file_name)

###################################################################
# Network Report
###################################################################

def get_daily_rev_exp(daily_site_report):

    ###################################################################
    # Daily revenue and expense per price type and site
    ###################################################################

    groupby_col = ['DAS Price Calculation Type', 'Site Group', 'Site', 'Date']
    values_col = ['Revenue', 'Expense', 'Prod. Fee']
    df = daily_site_report[groupby_col + values_col].groupby(groupby_col).sum().reset_index()

    return df

def get_summary_by_site_dict(daily_site_report, site_goals):

    summary_by_site_dict = {}

    ###################################################################
    # Prep
    ###################################################################

    last_delivery_date = daily_site_report['Date'].max()

    site_goals = site_goals.rename(columns={'IO Gross Revenue': 'Booked Gross Revenue',
                                            'IO Site Revenue': 'Booked Expense'})
    site_goals.loc[site_goals['Site'] == 'HL', ('Site Rate', 'Booked Expense')] = (0.0, 0.0)

    ###################################################################
    # IO + MTD
    ###################################################################

    groupby_col = ['BBR', 'Brand', 'DAS Line Item Name', 'Site']
    mtd = daily_site_report[groupby_col + ['Delivered', 'Billable', 'Clicks']].groupby(groupby_col).sum().reset_index()
    mtd = mtd.rename(columns={'Delivered': 'MTD Delivery', 'Billable': 'MTD Billable', 'Clicks': 'MTD Clicks'})

    df = pd.merge(site_goals, mtd, how='left', on=groupby_col)
    for col in ['MTD Delivery', 'MTD Billable', 'MTD Clicks']:
        df.loc[pd.isnull(df[col]), col] = 0

    ###################################################################
    # Projection
    ###################################################################

    temp_daily = fill_in_cc_uvs(daily_site_report, 'Delivered')
    projection = get_projection(temp_daily, 'Delivered', groupby_col, 'Date', last_delivery_date)
    df = pd.merge(df, projection, how='left', on=groupby_col)
    df.loc[pd.isnull(df['Projected Delivery']), 'Projected Delivery'] = 0
    
    def add_proj_billable(row):
        proj_delivery = row['Projected Delivery']
        if proj_delivery >= row['Aim Towards']:
            return row['Site Goal']
        return proj_delivery * (1.0 - row['MTD Disc'])

    df['Aim Towards'] = df['Site Goal'] / (1.0 - df['MTD Disc'])
    df['Projected Billable'] = df.apply(lambda row: add_proj_billable(row), axis=1)

    ###################################################################
    # Add amount
    ###################################################################

    def add_amount(row, delivery_col, rate_col):
        price_type = row['Price Calculation Type']
        if price_type == 'CPM':
            return row[delivery_col] / 1000.0 * row[rate_col]
        if price_type == 'CPUV':
            return row[delivery_col] * row[rate_col]

    df['MTD Gross Revenue'] = df.apply(lambda row: add_amount(row, 'Base Rate', 'MTD Billable'), axis=1)
    df['MTD Expense'] = df.apply(lambda row: add_amount(row, 'Site Rate', 'MTD Billable'), axis=1)

    df['Projected Gross Revenue'] = df.apply(lambda row: add_amount(row, 'Base Rate', 'Projected Billable'), axis=1)
    df['Projected Expense'] = df.apply(lambda row: add_amount(row, 'Site Rate', 'Projected Billable'), axis=1)

    ###################################################################
    # If there are less than 7 days' delivery, projection = IO
    ###################################################################

    days_delivering = last_delivery_date.day
    if days_delivering < 7:
        df['Projected Delivery'] = df['Site Goal']
        df['Projected Billable'] = df['Site Goal']
        df['Projected Gross Revenue'] = df['Booked Gross Revenue']
        df['Projected Expense'] = df['Booked Expense']

    ###################################################################
    # Booked & Delivering
    ###################################################################

    df['Booked & Delivering Gross Revenue'] = df.apply(lambda row: 0 if row['MTD Delivery'] == 0 else row['Booked Gross Revenue'], axis=1)
    df['Booked & Delivering Expense'] = df.apply(lambda row: 0 if row['MTD Delivery'] == 0 else row['Booked Expense'], axis=1)

    ###################################################################
    # Clean up
    ###################################################################

    for col in ['Aim Towards', 'Projected Billable', 'Booked Expense', 'Booked Gross Revenue',
                'Projected Expense', 'Projected Gross Revenue', 'Booked & Delivering Expense',
                'Booked & Delivering Gross Revenue']:
        df.loc[df['Site Goal'] < 0, col] = 0

    df['Site Group'] = df['Site'].apply(get_site_group)

    col = ['Price Calculation Type', 'BBR', 'Brand', 'DAS Line Item Name', 'Site',
           'Site Goal', 'MTD Disc', 'Aim Towards', 'MTD Delivery', 'MTD Billable', 'MTD Clicks',
           'Projected Delivery', 'Projected Billable', 'Site Rate', 'Base Rate', 'MTD Expense', 'MTD Gross Revenue',
           'Booked Expense', 'Booked Gross Revenue', 'Projected Expense', 'Projected Gross Revenue',
           'Booked & Delivering Expense', 'Booked & Delivering Gross Revenue',
           'Stage', 'Site Group']

    sortby = ['Price Calculation Type', 'BBR', 'Brand', 'DAS Line Item Name', 'Site']

    df = df[col].sort_values(sortby)

    summary_by_site_dict['raw'] = df

    ###################################################################
    # Summary
    ###################################################################

    groupby_col = ['Price Calculation Type', 'Site Group', 'Site']

    values_col = ['MTD Delivery', 'MTD Clicks', 'MTD Expense', 'MTD Gross Revenue',
                  'Booked Expense', 'Booked Gross Revenue',
                  'Projected Expense', 'Projected Gross Revenue',
                  'Booked & Delivering Expense', 'Booked & Delivering Gross Revenue']

    df = df[groupby_col + values_col].groupby(groupby_col).sum().reset_index()

    summary_by_site_dict['grouped'] = df

    return summary_by_site_dict

def up_nr2gsheet(nr2gsheet_dict):

    ###################################################################
    folder_id = '0B71ox_2Qc7gmU0dVMDhTUnk3Y0U'
    ###################################################################

    service = get_gsheet_service()

    # Find a file by its name
    ss_id = gdrive_get_file_id_by_name(nr2gsheet_dict['ss name'], folder_id)

    # Main
    for key in nr2gsheet_dict:
        if key == 'ss name':
            continue

        sheet_name = key
        df = nr2gsheet_dict[sheet_name]

        # Prep
        if 'Date' in df.columns.tolist():
            df['Date'] = [str(d) for d in df['Date']]  # date type isn't json serializable

        # Get sheet id
        sheet_id = gsheet_get_sheet_id_by_name(sheet_name, ss_id)

        # Clear existing values
        result = service.spreadsheets().values().clear(spreadsheetId=ss_id, range=sheet_name,
                                                       body={}).execute()

        # Upload new values
        values = [df.columns.tolist()] + df.values.tolist()
        result = service.spreadsheets().values().update(spreadsheetId=ss_id, range=sheet_name,
                                                        valueInputOption='USER_ENTERED',
                                                        body={'values': values}).execute()
    return None

def up_nr2gdrive(nr2gdrive_dict):

    ###################################################################
    folder_id = '0B71ox_2Qc7gmMFlPZXVrT1kwLXM'
    ###################################################################

    file_name = nr2gdrive_dict['file name']

    # Create file
    writer = pd.ExcelWriter(file_name)
    for key in nr2gdrive_dict:
        if key == 'file name':
            continue
        nr2gdrive_dict[key].to_excel(writer, key, index=False)
    writer.save()

    # Upload file
    save_in_gdrive(file_name, folder_id, 'application/vnd.ms-excel')
    os.remove(file_name)

    return None

###################################################################
# Partner Revenue Report
###################################################################

def get_partner_revenue_report(all1, site_goals, daily_sr):

    ##########################################################################
    # CPM
    ##########################################################################

    cpm = all1[(all1['Site'] != 'HL') &
               (all1['Site'] != 'Medical News Today') &
               (all1['Price Calculation Type'] == 'CPM') &
               (all1['Impressions/UVs'] > 0) &
               (pd.notnull(all1['Impressions/UVs']))]

    cpm.loc[pd.isnull(cpm['Clicks']), 'Clicks'] = 0
    cpm = cpm.rename(columns={'(DAS)BBR #': 'BBR'})

    groupby_col = ['Site', 'Price Calculation Type', 'BBR', 'Brand', 'DAS Line Item Name', 
                   'Creative size', 'Date']
    values_col = ['Impressions/UVs', 'Clicks']
    cpm = cpm[groupby_col + values_col].groupby(groupby_col).sum().reset_index()
    
    ##########################################################################
    # CPUV 
    ##########################################################################

    cpuv = daily_sr[(daily_sr['Site'] != 'HL') &
                    (daily_sr['Site'] != 'Medical News Today') &
                    (daily_sr['Price Calculation Type'] == 'CPUV')]

    col = ['Site', 'Price Calculation Type', 'BBR', 'Brand', 'DAS Line Item Name', 'Date', 'Billable']
    cpuv = cpuv[col].rename(columns={'Billable': 'Impressions/UVs'})

    ##########################################################################
    # Combine CPM and CPUV, and add rate and MTD disc
    ##########################################################################
    df = pd.concat([cpm, cpuv])
    df['Date'] = pd.to_datetime(df['Date'])

    join_on = ['Site', 'BBR', 'Brand', 'DAS Line Item Name']
    df = pd.merge(df, site_goals[join_on + ['Site Rate', 'MTD Disc']], how='left', on=join_on)

    ##########################################################################
    # Partner revenue a.k.a. Expense
    ##########################################################################

    def add_rev(row):
        if row['Site Rate'] is None:
            return None

        price_type = row['Price Calculation Type']
        if price_type == 'CPM':
            return row['Impressions/UVs'] / 1000.0 * row['Site Rate']
        if price_type == 'CPUV':
            return row['Impressions/UVs'] * row['Site Rate']

    df['Estimated Partner Revenue'] = df.apply(lambda row: add_rev(row), axis=1)
    df['Adjusted Estimated Partner Revenue'] = df['Estimated Partner Revenue'] * (1 - df['MTD Disc'])

    ##########################################################################
    # Add Campaign Name and Drugs IO Naming
    ##########################################################################

    das_bbr_camp = make_das(False, False)[['BBR', 'Campaign Name']].drop_duplicates()
    df = pd.merge(df, das_bbr_camp, how='left', on='BBR')

    max_date = df['Date'].max()
    sheet_name = str(max_date.year) + str(max_date.month).zfill(2)
    drugs_io_naming = get_drugs_io_naming(sheet_name)
    col = ['Internal Campaign Name', 'Campaign Name', 'Line Description', 'Placement']
    drugs_io_naming = drugs_io_naming[col]

    df = df.rename(columns={'Campaign Name': 'Internal Campaign Name',
                            'DAS Line Item Name': 'Line Description'})
    join_on = ['Internal Campaign Name', 'Line Description']
    df = pd.merge(df, drugs_io_naming, how='left', on=join_on)

    ##########################################################################
    # Clean up
    ##########################################################################

    col = ['Site', 'Price Calculation Type', 'Internal Campaign Name', 'Line Description', 'Creative size',
           'Date', 'Impressions/UVs', 'Clicks', 'Estimated Partner Revenue',
           'Adjusted Estimated Partner Revenue', 'Site Rate', 'MTD Disc',
           'BBR', 'Brand', 'Campaign Name', 'Placement']

    sortby = ['Site', 'Price Calculation Type', 'Internal Campaign Name', 'Line Description',
              'Creative size', 'Date']

    df = df[col].sort_values(sortby)

    return df

def get_partner_revrep_check(daily_site_report):

    df = daily_site_report[daily_site_report['Site Group'] == 'HW']

    def add_amount(row, unit):
        price_type = row['Price Calculation Type']
        if price_type == 'CPM':
            return row[unit] / 1000.0 * row['Site Rate']
        if price_type == 'CPUV':
            return row[unit] * row['Site Rate']
        return 0

    unit_col = ['Delivered', 'Adjusted w/ Discrepancy', 'Billable']
    amount_col = []
    for col in unit_col:
        df['$ ' + col] = df.apply(lambda row: add_amount(row, col), axis=1)
        amount_col.append('$ ' + col)

    groupby_col = ['Site', 'Price Calculation Type']
    df = df[groupby_col + unit_col + amount_col + ['Clicks']].groupby(groupby_col).sum().reset_index()

    return df

def up_partner_revrep2gdrive(partner_revrep2gdrive_dict):

    ###################################################################
    folder_id = '0B71ox_2Qc7gmVTA0cnExM1lqYlU'
    ###################################################################

    file_name = partner_revrep2gdrive_dict['file name']

    # Create file
    writer = pd.ExcelWriter(file_name)
    for key in partner_revrep2gdrive_dict:
        if key == 'file name':
            continue
        partner_revrep2gdrive_dict[key].to_excel(writer, key, index=False)
    writer.save()

    # Upload file
    save_in_gdrive(file_name, folder_id, 'application/vnd.ms-excel')
    os.remove(file_name)

    return None

def get_check_mapping_dict(all1, site_goals):

    first_date = all1['Date'].min()
    mo = first_date.month
    year = first_date.year
    das_month = str(mo) + '/' + str(year)

    das = make_das(use_scheduled_units=False, export=False)

    check_mapping_dict = {}

    #############################################################################################
    # 1. CPM no match in Salesforce
    # Delivery without a match of ((DAS) BBR #, Brand, Line Description) in Salesforce
    #############################################################################################
    
    no_match = all1[(all1['Price Calculation Type'] == 'CPM') &
                    (all1['Match in DAS'] == 0) &
                    (all1['Impressions/UVs'] > 0)]

    no_match = bbr2cm(no_match, '(DAS)BBR #', das)

    groupby_col = ['Campaign Manager', '(DAS)BBR #', 'Order', 'Line item', 'DFP Creative ID', 'Creative', 'DAS Line Item Name', 'Site']
    value_col = ['Impressions/UVs']
    rename_dict = {'Impressions/UVs': 'Impressions'}
    sortby = ['Campaign Manager', 'Order', 'Line item', 'Creative', 'DAS Line Item Name', 'Site']

    fillna_col = ['Campaign Manager', '(DAS)BBR #', 'Site']
    fillna_str = '_TEMP_NONE_'
    for col in fillna_col:
        no_match[col] = no_match[col].fillna(fillna_str)  # For grouping

    no_match = no_match[groupby_col + value_col].groupby(groupby_col).sum().reset_index(drop=False)
    no_match = no_match.rename(columns=rename_dict).sort_values(sortby)

    for col in fillna_col:
        no_match[col] = no_match[col].str.replace(fillna_str, '')

    check_mapping_dict['CPM no match in Salesforce'] = no_match

    #############################################################################################
    # 2. CPUV no match
    # Either the tab name not found in Goals Sheet, or Goals Sheet not matching Salesforce
    #############################################################################################

    no_match = all1[(all1['Price Calculation Type'] == 'CPUV') &
                    (all1['Match in DAS'] == 0) &
                    (all1['Impressions/UVs'] > 0)]

    col = ['(Order)BBR #', 'DAS Line Item Name', 'Original Report Tab Name', 'Report Tab Name', 'Site']
    sortby = ['Report Tab Name', 'Site']
    no_match = no_match[col].drop_duplicates().sort_values(sortby)

    check_mapping_dict['CPUV no match'] = no_match

    #############################################################################################
    # 3. CPM live in Salesforce no delivery
    #############################################################################################

    live_in_sf = das_filtered(das, das_month)
    live_in_sf = live_in_sf[(live_in_sf['Price Calculation Type'] == 'CPM') &
                            (live_in_sf['Stage'] == 'Booked Live')]
    live_in_sf = live_in_sf[['Campaign Manager', 'BBR', 'Brand', 'Campaign Name', 'Line Item Number', 'Line Description']]

    in_dfp = all1[all1['Price Calculation Type'] == 'CPM'][['(Order)BBR #', 'Brand', 'DAS Line Item Name']].rename(
        columns={'(Order)BBR #': 'BBR', 'DAS Line Item Name': 'Line Description'}).drop_duplicates()
    in_dfp['In DFP'] = 1

    live_in_sf = pd.merge(live_in_sf, in_dfp, how='left', on=['BBR', 'Brand', 'Line Description'])
    live_in_sf = live_in_sf[live_in_sf['In DFP'] != 1].drop('In DFP', axis=1)

    col = ['Campaign Manager', 'BBR', 'Campaign Name', 'Line Item Number', 'Line Description']
    sortby = ['Campaign Manager', 'Campaign Name', 'Line Item Number']
    live_in_sf = live_in_sf[col].sort_values(sortby)

    check_mapping_dict['CPM live in Salesforce no delivery'] = live_in_sf

    #############################################################################################
    # 4. Delivering without a goal
    #############################################################################################
    
    groupby_col = ['Price Calculation Type', '(DAS)BBR #', 'Brand', 'DAS Line Item Name', 'Site', 'Date']
    mtd = all1[((all1['Price Calculation Type'] == 'CPM') | (all1['Price Calculation Type'] == 'CPUV')) &
               (all1['Impressions/UVs'] != 0)][groupby_col + ['Impressions/UVs']]
    mtd = mtd.groupby(groupby_col).sum().reset_index()
    mtd = pd.merge(mtd, site_goals.rename(columns={'BBR': '(DAS)BBR #'}), how='left',
                   on=['Price Calculation Type', '(DAS)BBR #', 'Brand', 'DAS Line Item Name', 'Site'])

    no_goal = mtd[(pd.isnull(mtd['Site Goal']) | (mtd['Site Goal'] == 0)) & (mtd['Site'] != 'HL')]
    no_goal = bbr2camp(no_goal, '(DAS)BBR #', das)
    no_goal = bbr2cm(no_goal, '(DAS)BBR #', das)
    
    col = ['Price Calculation Type', 'Campaign Manager', 'Site', 'Date', '(DAS)BBR #',
           'Campaign Name', 'DAS Line Item Name', 'Impressions/UVs']
    sortby = ['Price Calculation Type', 'Campaign Manager', 'Campaign Name', 'DAS Line Item Name', 'Site', 'Date']
    no_goal = no_goal[col].sort_values(sortby)

    check_mapping_dict['delivery without goal'] = no_goal

    return check_mapping_dict

def up_check_mapping2gsheet(check_mapping_dict):

    ###################################################################
    folder_id = '0B71ox_2Qc7gmSU9zc3NfZmtJd3c'
    ###################################################################

    service = get_gsheet_service()

    # Find a file by its name
    ss_id = gdrive_get_file_id_by_name(check_mapping_dict['ss name'], folder_id)

    # Main
    for key in check_mapping_dict:
        if key == 'ss name':
            continue

        sheet_name = key
        df = check_mapping_dict[sheet_name].fillna('')

        # Prep
        if 'Date' in df.columns.tolist():
            df['Date'] = [str(d) for d in df['Date']]  # date type isn't json serializable

        # Clear existing values
        result = service.spreadsheets().values().clear(spreadsheetId=ss_id, range=sheet_name,
                                                       body={}).execute()

        # Upload new values
        values = [df.columns.tolist()] + df.values.tolist()
        result = service.spreadsheets().values().update(spreadsheetId=ss_id, range=sheet_name,
                                                        valueInputOption='USER_ENTERED',
                                                        body={'values': values}).execute()
    return None

###################################################################
# Drugs.com CPM MTD delivery per Campaign/Placement along with
# Aim Towards and pacing
###################################################################

def get_drugs_mtd_dict(all1, site_goals):

    ##########################################################################
    # Prep
    ##########################################################################

    max_date = all1['Date'].max()
    mo = max_date.month
    year = max_date.year
    das_month = str(mo) + '/' + str(year)
    
    df = all1[(all1['Site'] == 'Drugs.com') & (all1['Price Calculation Type'] == 'CPM') &
              (all1['Impressions/UVs'] > 0) & (pd.notnull(all1['Impressions/UVs']))]

    groupby_col = ['(DAS)BBR #', 'Brand', 'DAS Line Item Name']
    values_col = ['Impressions/UVs']
    df = df[groupby_col + values_col].groupby(groupby_col).sum().reset_index()
    
    df = df.rename(columns={'(DAS)BBR #': 'BBR'})

    ##########################################################################
    # Add Site Goal & MTD disc
    ##########################################################################

    drugs_site_goals = site_goals[site_goals['Site'] == 'Drugs.com']
    join_on = ['BBR', 'Brand', 'DAS Line Item Name']
    df = pd.merge(df, drugs_site_goals[join_on + ['Site Goal', 'MTD Disc']], how='left', on=join_on)
    
    ##########################################################################
    # Add Aim Towards
    ##########################################################################
    
    def add_aim_towards(row):
        goal = row['Site Goal']
        disc = row['MTD Disc']
        
        if goal is None:
            return None
        if disc is None:
           disc = 0
        return goal/(1-disc)

    df['Aim Towards'] = df.apply(lambda row: add_aim_towards(row), axis=1)

    ##########################################################################
    # Add Campaign Start Date and End Date
    ##########################################################################

    das = make_das(False, False)
    das_thismonth = das_filtered(das, das_month)

    rename_dict = {'Line Description': 'DAS Line Item Name'}
    to_add = ['Start Date', 'End Date']

    df = pd.merge(df, das_thismonth.rename(columns=rename_dict)[join_on + to_add], how='left', on=join_on)

    ##########################################################################
    # Add Daily Ave Pacing
    ##########################################################################

    mo_start_date, mo_end_date = start_end_month(max_date)
    real_mo_end_date = mo_end_date
    mo_end_date = date(mo_end_date.year, mo_end_date.month, 25)  # Where possible, Drugs aim to complete a campaign/line by 25th

    df['Campaign Start Date'] = [mo_start_date if sd <= mo_start_date else sd for sd in df['Start Date']]
    df['Real Campaign End Date'] = [real_mo_end_date if ed >= real_mo_end_date else ed for ed in df['End Date']]
    df['Campaign End Date'] = [mo_end_date if ed >= mo_end_date else ed for ed in df['End Date']]
    df['Days'] = df.apply(lambda row: (row['Campaign End Date'] - row['Campaign Start Date']).days + 1, axis=1)
    df['Past Days'] = df.apply(lambda row: (max_date - row['Campaign Start Date']).days + 1, axis=1)
    df.loc[df['Past Days'] < 0, 'Past Days'] = 0

    df['Pacing (Daily Ave)'] = df['Impressions/UVs']/(df['Aim Towards']/df['Days']*df['Past Days'])

    ##########################################################################
    # Add Daily Ave Needed
    ##########################################################################

    df['Left'] = df['Aim Towards'] - df['Impressions/UVs']
    df.loc[df['Left'] < 0, 'Left'] = 0

    df['Need (Daily Ave)'] = df['Left']/(df['Days']-df['Past Days'])

    ##########################################################################
    # Add Yesterday's delivery & Pacing based on yesterday's delivery
    ##########################################################################
    
    daily = all1[(all1['Site'] == 'Drugs.com') & (all1['Price Calculation Type'] == 'CPM') &
              (all1['Impressions/UVs'] > 0) & (pd.notnull(all1['Impressions/UVs'])) & 
              (all1['Date'] == max_date)]

    groupby_col = ['(DAS)BBR #', 'Brand', 'DAS Line Item Name']
    values_col = ['Impressions/UVs']
    daily = daily[groupby_col + values_col].groupby(groupby_col).sum().reset_index()

    daily = daily.rename(columns={'(DAS)BBR #': 'BBR', 'Impressions/UVs': 'Yesterday Delivery'})
    df = pd.merge(df, daily, how='left', on=join_on)

    df['Pacing (Yesterday)'] = df['Yesterday Delivery']/df['Need (Daily Ave)']
    
    ##########################################################################
    # Comments
    ##########################################################################

    cols = ('Pacing (Daily Ave)', 'Need (Daily Ave)', 'Pacing (Yesterday)')    

    df.loc[df['Impressions/UVs'] > df['Aim Towards'], cols] = 'Hit the goal'
    df.loc[df['Past Days'] == 0, cols] = 'Not yet started'
    df.loc[df['Campaign End Date'] <= max_date, cols] = 'Ended'

    ##########################################################################
    # Add Campaign Name and Drugs IO Naming
    ##########################################################################

    das_bbr_camp = make_das(False, False)[['BBR', 'Campaign Name']].drop_duplicates()
    df = pd.merge(df, das_bbr_camp, how='left', on='BBR')

    sheet_name = str(max_date.year) + str(max_date.month).zfill(2)
    drugs_io_naming = get_drugs_io_naming(sheet_name)
    col = ['Internal Campaign Name', 'Campaign Name', 'Line Description', 'Placement']
    drugs_io_naming = drugs_io_naming[col]

    df = df.rename(columns={'Campaign Name': 'Internal Campaign Name',
                            'DAS Line Item Name': 'Line Description'})
    join_on = ['Internal Campaign Name', 'Line Description']
    df = pd.merge(df, drugs_io_naming, how='left', on=join_on)

    ##########################################################################
    # Clean up
    ##########################################################################

    df = df[pd.notnull(df['Site Goal'])]

    if max_date.day < 25:
        col = ['Campaign Name', 'Placement', 'Impressions/UVs', 'Aim Towards', 'Left', 'Need (Daily Ave)', 'Pacing (Daily Ave)', 
               'Yesterday Delivery', 'Pacing (Yesterday)', 'Site Goal', 'MTD Disc', 'Campaign End Date']
        rename_dict = {'Impressions/UVs': 'HL DFP MTD', 'Campaign End Date': 'End Date (Max 25th)'}
    else:
        col = ['Campaign Name', 'Placement', 'Impressions/UVs', 'Aim Towards', 'Left',
               'Yesterday Delivery', 'Site Goal', 'MTD Disc', 'Real Campaign End Date']
        rename_dict = {'Impressions/UVs': 'HL DFP MTD', 'Real Campaign End Date': 'End Date'}
      
    sortby = ['Campaign Name', 'Placement']
    df = df[col].sort_values(sortby).rename(columns=rename_dict)

    return {'df': df, 'max date': max_date}

def up_drugs_mtd(drugs_mtd_dict):

    ###################################################################
    folder_id = '0B71ox_2Qc7gmQUFPZmQyRTBnX1E'
    ###################################################################

    ############################################
    # Create a new google sheet
    ############################################
    
    gdrive_service = get_gdrive_service()
    gsheet_service = get_gsheet_service()

    max_date = drugs_mtd_dict['max date']
    year = str(max_date.year)
    mo = str(max_date.month).zfill(2)
    day = str(max_date.day).zfill(2)

    file_data = {'name': 'Drugs.com_CPM_MTD_HL_DFP_Imps_Through_' + year + '_' + mo + '_' + day,
                 'parents': [folder_id],
                 'mimeType': 'application/vnd.google-apps.spreadsheet'}
    file_info = gdrive_service.files().create(body=file_data).execute()
    file_id = file_info['id']

    ############################################
    # Upload
    ############################################

    df = drugs_mtd_dict['df']
    df = df.fillna('')

    # Upload isn't doable with date type
    for col in df.columns.tolist():
        if 'End Date' in col:
            df[col] = [str(d) for d in df[col]]

    values = [df.columns.tolist()] + df.values.tolist()
    result = gsheet_service.spreadsheets().values().update(spreadsheetId=file_id, range='Sheet1',
                                                           valueInputOption='USER_ENTERED', body={'values': values}).execute()
    
    return file_id

def format_drugs_mtd(file_id):
   
    service = get_gsheet_service()
    sheet_name = 'Sheet1' 

    # Find the sheet id and basic info
    sheet_id = gsheet_get_sheet_id_by_name(sheet_name, file_id)
    
    # Get values > header, # of col, # of row
    result = service.spreadsheets().values().get(spreadsheetId=file_id, range=sheet_name, valueRenderOption='UNFORMATTED_VALUE').execute()
    values = result.get('values', [])

    header = values[0]
    n_col = len(header)
    n_row = len(values)

    # Freeze top row and left colums
    freeze = [{'updateSheetProperties': {'properties': {'sheetId': sheet_id,
                                                        'gridProperties': {'frozenRowCount': 1}},
                                         'fields': 'gridProperties(frozenRowCount)'}}]

    # Wrap header
    wrap = [{'updateCells': {'rows': [{'values': [{'userEnteredFormat': {'wrapStrategy': 'WRAP'}}] * n_col}],
                             'fields': 'userEnteredFormat.wrapStrategy',
                             'range': {'sheetId': sheet_id,
                                       'startRowIndex': 0,
                                       'endRowIndex': 1,
                                       'startColumnIndex': 0,
                                       'endColumnIndex': n_col}}}]

    # Font
    font = [{'updateCells': {'rows': [{'values': [{'userEnteredFormat': {'textFormat': {'fontFamily': 'Roboto',
                                                                                        'fontSize': 10}}}] * n_col}] * n_row,
                             'fields': 'userEnteredFormat.textFormat(fontFamily, fontSize)',
                             'range': {'sheetId': sheet_id,
                                       'startRowIndex': 0,
                                       'endRowIndex': n_row,
                                       'startColumnIndex': 0,
                                       'endColumnIndex': n_col}}}]
    
    # Value formatting
    def make_vf_dict(sheet_name, col, format_type):
        i_col = header.index(col)

        if format_type == 'integer':
            pattern = '###,###,##0'
        elif format_type == 'percent':
            pattern = '#0.0%'
        
        return {'repeatCell': {'range': {'sheetId': sheet_id,
                                         'startRowIndex': 1,
                                         'endRowIndex': n_row,
                                         'startColumnIndex': i_col,
                                         'endColumnIndex': i_col+1},
                               'cell': {'userEnteredFormat': {'numberFormat': {'type': 'NUMBER',
                                                                               'pattern': pattern}}},
                               'fields': 'userEnteredFormat.numberFormat'}} 
    
    int_col = ['HL DFP MTD', 'Aim Towards', 'Left', 'Need (Daily Ave)', 'Yesterday Delivery', 'Site Goal'] 
    percent_col = ['Pacing (Daily Ave)', 'Pacing (Yesterday)', 'MTD Disc']

    value_formatting = []
    for col in int_col:
        if col in header:
            value_formatting.append(make_vf_dict(sheet_name, col, 'integer'))
    for col in percent_col:
        if col in header:
            value_formatting.append(make_vf_dict(sheet_name, col, 'percent'))

    # Header color
    def make_color_header_dict(sheet_name, col, color):
        i_col = header.index(col)

        if color == 'green':
            color_dict = {'red': .851, 'green': .918, 'blue': .827, 'alpha': 1}
        elif color == 'yellow':
            color_dict = {'red': 1, 'green': .949, 'blue': .8, 'alpha': 1}
        else:
            color_dict = {'red': .953, 'green': .953, 'blue': .953, 'alpha': 1}
 
        return {'updateCells': {'rows': [{'values': [{'userEnteredFormat': {'backgroundColor': color_dict}}]}],
                                'fields': 'userEnteredFormat.backgroundColor',
                                'range': {'sheetId': sheet_id,
                                          'startRowIndex': 0,
                                          'endRowIndex': 1,
                                          'startColumnIndex': i_col,
                                          'endColumnIndex': i_col+1}}}

    green_col = ['Campaign Name', 'Placement', 'HL DFP MTD', 'Aim Towards', 'Left']
    yellow_col = ['Need (Daily Ave)', 'Pacing (Daily Ave)', 'Yesterday Delivery', 'Pacing (Yesterday)']
    grey_col = ['Site Goal', 'MTD Disc', 'End Date (Max 25th)', 'End Date']

    color_header = []
    for col in green_col:
        if col in header:
            color_header.append(make_color_header_dict(sheet_name, col, 'green'))
    for col in yellow_col:
        if col in header:
            color_header.append(make_color_header_dict(sheet_name, col, 'yellow'))
    for col in grey_col:
        if col in header:
            color_header.append(make_color_header_dict(sheet_name, col, 'grey'))

    # Column width
    i_col = header.index('Placement')
    width = [{'updateDimensionProperties': {'range': {'sheetId': sheet_id,
                                                      'dimension': 'COLUMNS',
                                                      'startIndex': i_col,
                                                      'endIndex': i_col+1},
                                            'properties': {'pixelSize': 175},
                                            'fields': 'pixelSize'}}]

    # Send requests
    all_requests = freeze + wrap + font + value_formatting + color_header + width
    result = service.spreadsheets().batchUpdate(spreadsheetId=file_id, body={'requests': all_requests}).execute()

def get_monthly_uvs(all1, cpuv_goals):
    # Format UVs
    uvs = all1[all1['Price Calculation Type'] == 'CPUV'].rename(columns={'DAS Line Item Name': 'Line Description'})
    col = ['Campaign Name', 'Line Description', 'Site', 'Impressions/UVs']
    uvs = pd.pivot_table(uvs[col], index=['Campaign Name', 'Line Description'], columns=['Site'], values='Impressions/UVs', fill_value=0, aggfunc=np.sum).reset_index(drop=False)
    
    site_col = []
    for col in uvs.columns.tolist():
        if col not in ['Campaign Name', 'Line Description']:
            site_col.append(col)

    # Join with CPUV Goals Sheet
    col = ['BBR', 'Campaign Name', 'Start Date', 'End Date', 'Line Description', 'Competitive Conquesting', 'Goal']
    goals = cpuv_goals[col]
    combined = pd.merge(goals, uvs, how='left', on=['Campaign Name', 'Line Description'])

    # Clean up
    combined[site_col] = combined[site_col].fillna(0)
    combined['Total'] = 0
    combined['Pacing'] = 0

    header = ['BBR', 'Campaign Name', 'Start Date', 'End Date', 'Line Description', 'Competitive Conquesting'] + site_col + ['Total', 'Goal', 'Pacing']
    combined = combined[header].sort_values(['Campaign Name', 'Line Description']).reset_index(drop=True)

    # Formula columns
    def col_name2letter(col):
        idx = header.index(col) + 1
        return opx.utils.get_column_letter(idx)

    site_col_letter_list = [col_name2letter(col) for col in site_col]
    total_col_letter = col_name2letter('Total')
    goal_col_letter = col_name2letter('Goal')

    def get_total_uvs(row):
        row_index = str(row.name + 2)
        output = '+'.join([(site_col_letter + row_index) for site_col_letter in site_col_letter_list])
        output = '=' + output
        return output

    def get_pacing(row):
        row_index = str(row.name + 2)
        output = '=IF(' + total_col_letter + row_index + '>=' + goal_col_letter + row_index + ','
        output += '"Delivered in Full",'
        output += '(' + total_col_letter + row_index + '/(DAY(TODAY()) - 1))/(' + goal_col_letter + row_index + '/DAY(EOMONTH(TODAY(),0))))'
        return output

    combined['Total'] = combined.apply(lambda row: get_total_uvs(row), axis=1)
    combined['Pacing'] = combined.apply(lambda row: get_pacing(row), axis=1)

    return combined

def up_monthly_uvs2gsheet(monthly_uvs2gsheet_dict):
    
    ###################################################################
    folder_id = '1rQfci0UV_mVxjsTHYELyiJx_9MqZkd7z'
    ###################################################################

    service = get_gsheet_service()

    # Content
    df = monthly_uvs2gsheet_dict['content']

    # Find a file by its name. If doesnt exist, create.
    file_name = monthly_uvs2gsheet_dict['ss name']
    ss_id = gdrive_get_file_id_by_name(file_name, folder_id)
    if ss_id is None:
        csv_file_name = file_name + '.csv'
        df.to_csv(csv_file_name, index=False)
        file_id = save_csv_as_gsheet_in_gdrive(file_name, folder_id, csv_file_name)
        os.remove(csv_file_name)
        return file_id

    # Get sheet id
    sheet_name = file_name
    sheet_id = gsheet_get_sheet_id_by_name(sheet_name, ss_id)

    # Prep
    for col in ['Start Date', 'End Date']:
        df[col] = [str(d) for d in df[col]]  # date type isn't json serializable
    df = df.fillna('')

    values = [df.columns.tolist()] + df.values.tolist()
    
    # Clear existing values
    result = service.spreadsheets().values().clear(spreadsheetId=ss_id, range=sheet_name,
                                                   body={}).execute()

    # Upload new values
    result = service.spreadsheets().values().update(spreadsheetId=ss_id, range=sheet_name,
                                                    valueInputOption='USER_ENTERED',
                                                    body={'values': values}).execute()
    return ss_id

def format_monthly_uvs(year, mo, ss_id):

    service = get_gsheet_service()

    # Find the sheet (name of sheet is the same as name of file)
    ss_metadata = service.spreadsheets().get(spreadsheetId=ss_id).execute()
    ss_name = ss_metadata['properties']['title']

    for sheet_metadata in ss_metadata['sheets']:
        if sheet_metadata['properties']['title'] == ss_name:
            sheet_id = sheet_metadata['properties']['sheetId']

    # Get values
    result = service.spreadsheets().values().get(
        spreadsheetId=ss_id, range=ss_name, valueRenderOption='UNFORMATTED_VALUE').execute()
    values = result.get('values', [])

    header = values[0]
    i_sites_start = header.index('Competitive Conquesting') + 1
    i_campaign = header.index('Campaign Name')
    i_ld = header.index('Line Description')

    n_row = len(values)
    n_col = len(header)

    sites = []
    for i in range(len(header)):
        if i < i_sites_start:
            continue
        if header[i] == 'Total':
            break
        sites.append(header[i])

    ###############################################
    # Color site goals
    ###############################################

    # Get CPUV goals
    DIR_PICKLES = PATH2PICKLES + '/' + PREFIX4ALWAYS_UP2DATE + str(year) + '_' + str(mo).zfill(2)
    with open(DIR_PICKLES + '/' + 'cpuv_goals.pickle', 'rb') as f:
        cpuv_goals = pickle.load(f)

    # Loop through rows of site delivery columns
    site2goal_col = {'HL': 'HL Goal', 'Drugs.com': 'Drugs Goal', 'GoodRx': 'GoodRx Goal', 
                     'Medical News Today': 'MNT Goal', 'Breastcancer.org': 'BCO Goal'}

    def has_goal(campaign, ld, site):
        row = cpuv_goals[(cpuv_goals['Campaign Name'] == campaign) &
                         (cpuv_goals['Line Description'] == ld)]
        if len(row) < 1:
            return False

        col = site2goal_col[site]
        if row[col].tolist()[0] > 0:
            return True
        return False

    color_values = []
    color_site_goals = [{'updateCells': {'rows': color_values,
                                         'fields': 'userEnteredFormat.backgroundColor',
                                         'range': {'sheetId': sheet_id,
                                                   'startRowIndex': 1,
                                                   'endRowIndex': n_row,
                                                   'startColumnIndex': i_sites_start,
                                                   'endColumnIndex': i_sites_start + len(sites)}}}]

    white = {'red': 1, 'green': 1, 'blue': 1, 'alpha': 1}
    grey = {'red': .663, 'green': .663, 'blue': .663, 'alpha': .663}
    for i in range(1, n_row):
        row = values[i]
        color_row = []
        for j in range(len(sites)):
            campaign = row[i_campaign]
            ld = row[i_ld]
            site = sites[j]
            if has_goal(campaign, ld, site):
                bg = white
            else:
                bg = grey
            color_row.append({'userEnteredFormat': {'backgroundColor': bg}})
        color_values.append({'values': color_row})

    ###############################################
    # Other formatting 
    ###############################################

    # Color header
    green = {'red': .851, 'green': .918, 'blue': .827, 'alpha': 1}
    color_header = [{'updateCells': {'rows': [{'values': [{'userEnteredFormat': {'backgroundColor': green}}] * n_col}],
                                     'fields': 'userEnteredFormat.backgroundColor',
                                     'range': {'sheetId': sheet_id,
                                               'startRowIndex': 0,
                                               'endRowIndex': 1,
                                               'startColumnIndex': 0,
                                               'endColumnIndex': n_col}}}]

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

    # Clip
    clip = [{'updateCells': {'rows': [{'values': [{'userEnteredFormat': {'wrapStrategy': 'CLIP'}}] * i_sites_start}] * (n_row - 1),
                             'fields': 'userEnteredFormat.wrapStrategy',
                             'range': {'sheetId': sheet_id,
                                       'startRowIndex': 1,
                                       'endRowIndex': n_row,
                                       'startColumnIndex': 0,
                                       'endColumnIndex': i_sites_start}}}]

    # Color grouped
    yellow = {'red': 1, 'green': .949, 'blue': .8, 'alpha': 1}
    color_grouped = [{'updateCells': {'rows': [{'values': [{'userEnteredFormat': {'backgroundColor': yellow}}] * 2}] * (n_row - 1),
                                      'fields': 'userEnteredFormat.backgroundColor',
                                      'range': {'sheetId': sheet_id,
                                                'startRowIndex': 1,
                                                'endRowIndex': n_row,
                                                'startColumnIndex': header.index('Total'),
                                                'endColumnIndex': header.index('Goal') + 1}}}]

    # Date formatting
    date_format = [{'repeatCell': {'range': {'sheetId': sheet_id,
                                             'startRowIndex': 1,
                                             'endRowIndex': n_row,
                                             'startColumnIndex': header.index('Start Date'),
                                             'endColumnIndex': header.index('End Date') + 1},
                                  'cell': {'userEnteredFormat': {'numberFormat': {'type': 'DATE',
                                                                                  'pattern': 'm/d/yyyy'}}},
                                  'fields': 'userEnteredFormat.numberFormat'}}]

    # Integer formatting
    int_format = [{'repeatCell': {'range': {'sheetId': sheet_id,
                                            'startRowIndex': 1,
                                            'endRowIndex': n_row,
                                            'startColumnIndex': i_sites_start,
                                            'endColumnIndex': header.index('Goal') + 1},
                                  'cell': {'userEnteredFormat': {'numberFormat': {'type': 'NUMBER',
                                                                                  'pattern': '###,###,##0'}}},
                                  'fields': 'userEnteredFormat.numberFormat'}}]

    # Percent formatting
    per_format = [{'repeatCell': {'range': {'sheetId': sheet_id,
                                            'startRowIndex': 1,
                                            'endRowIndex': n_row,
                                            'startColumnIndex': header.index('Pacing'),
                                            'endColumnIndex': header.index('Pacing') + 1},
                                  'cell': {'userEnteredFormat': {'numberFormat': {'type': 'NUMBER',
                                                                                  'pattern': '###,##0.0%'}}},
                                  'fields': 'userEnteredFormat.numberFormat'}}]

    # Clear all formatting first
    clear_request = [{'updateCells': {'range': {'sheetId': sheet_id}, 'fields': 'userEnteredFormat'}}]
    result = service.spreadsheets().batchUpdate(spreadsheetId=ss_id, body={'requests': clear_request}).execute()

    # Send requests
    requests = color_site_goals + color_header + freeze + basic_filter + wrap + clip + color_grouped + date_format + int_format + per_format
    result = service.spreadsheets().batchUpdate(spreadsheetId=ss_id, body={'requests': requests}).execute()



