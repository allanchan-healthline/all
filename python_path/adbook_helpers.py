from NEW_helpers import *

from yattag import Doc, indent

import pandas as pd
import numpy as np
from datetime import datetime

pd.options.mode.chained_assignment = None  # default='warn'

############################################################################
# List of Campaign dict
############################################################################

def get_ab_campaign_dict_list(all1, site_goals, third_party_imps):
    """Return a tuple of (campaign_dict_list, last_delivery_date).
    campaign_dict_list is a list of dictionaries where each dictionary contains one campaign's info from Salesforce, 
    site goals/discrepancies, and MTD delivery. Each line item has its own dictionary in campaign_dict['line_dict_list'].
    """

    ##################################################################################
    # Basics
    ##################################################################################

    last_delivery_date = all1['Date'].max()
    month_start, month_end = start_end_month(last_delivery_date)
    das_month = str(month_start.month) + '/' + str(month_start.year)
        
    ##################################################################################
    # Format delivery data
    ##################################################################################

    delivery = all1[(all1['Price Calculation Type'] == 'CPM') | (all1['Price Calculation Type'] == 'CPUV')]
    delivery = delivery.rename(columns={'(DAS)BBR #': 'BBR', 'DAS Line Item Name': 'Line Description'})
    delivery.loc[pd.isnull(delivery['Creative size']), 'Creative size'] = 'N/A'

    groupby_col = ['BBR', 'Brand', 'Line Description', 'Site', 'Creative size', 'Date']
    delivery = delivery[groupby_col + ['Impressions/UVs']].groupby(groupby_col).sum().reset_index()

    ##################################################################################
    # Format site goals data
    ##################################################################################

    site_goals = site_goals.rename(columns={'DAS Line Item Name': 'Line Description'})
    
    ##################################################################################
    # Use abbr. for Site
    ##################################################################################

    site_abbr_dict = {'Black Health Matters': 'BHM',
                      'Dr.Gourmet': 'DR.G',
                      'Drugs.com': 'Drugs',
                      'eHow': 'eHow',
                      'EmpowHer': 'EPH',
                      'eMedTV': 'eMed',
                      'GoodRx': 'GRX',
                      'HL': 'HL',
                      'Livestrong': 'LS',
                      'Medical News Today': 'MNT'}

    for site in site_abbr_dict:
        delivery.loc[delivery['Site'] == site, 'Site'] = site_abbr_dict[site]
        site_goals.loc[site_goals['Site'] == site, 'Site'] = site_abbr_dict[site]

    ##################################################################################
    # Add site_size to delivery data
    ##################################################################################
    
    def add_site_size(row):
        if row['Creative size'] == 'N/A':
            return row['Site']
        return row['Site'] + ' ' + row['Creative size']
    delivery['site_size'] = delivery.apply(lambda row: add_site_size(row), axis=1)

    ##################################################################################
    # Format third party data
    ##################################################################################

    third_party_imps = third_party_imps[['BBR', 'DAS Line Item Name', 'Date', 'Impressions (3rd Party)']]
    third_party_imps = third_party_imps.rename(columns={'DAS Line Item Name': 'Line Description',
                                                        'Impressions (3rd Party)': '3rd Party'})

    ##################################################################################
    # Loop through campaigns a.k.a. bbrs
    ##################################################################################

    das = make_das(False, False)
    das = das_filtered(das, das_month)  # This month's DAS, excluding SEM

    campaign_dict_list = []

    def get_campaign_dict(bbr):

        campaign_dict = {}
        campaign_dict['bbr'] = bbr

        ##################################################################################
        # DAS info
        ##################################################################################

        mini_das = das[das['BBR'] == bbr].sort_values(['Line Item Number', 'Line Description'])
        campaign_dict['name'] = ', '.join(mini_das['Campaign Name'].drop_duplicates().tolist())
        campaign_dict['cm'] = ', '.join(mini_das['Campaign Manager'].drop_duplicates().tolist())
        campaign_dict['am'] = ', '.join(mini_das['Account Manager'].drop_duplicates().tolist())

        ##################################################################################
        # Select data
        ##################################################################################

        mini_delivery = delivery[delivery['BBR'] == bbr]
        mini_site_goals = site_goals[site_goals['BBR'] == bbr]
        mini_third_party_imps = third_party_imps[third_party_imps['BBR'] == bbr]

        ##################################################################################
        # Per line item
        ##################################################################################

        line_dict_list = []

        def get_line_dict(line_das):

            line_dict = {}

            ##################################################################################
            # DAS info
            ##################################################################################

            line_dict['oli'] = line_das['OLI']
            line_dict['num'] = line_das['Line Item Number']
            line_dict['name'] = line_das['Line Description']
            line_dict['stage'] = line_das['Stage']
            line_dict['v_source'] = line_das['Viewability Source']
            line_dict['v_guarantee'] = line_das['Viewability']
            line_dict['blocking'] = line_das['Blocking System']
            line_dict['type'] = line_das['Price Calculation Type']
            line_dict['base_rate'] = line_das['Base Rate']
            line_dict['prod_rate'] = line_das['Baked-In Production Rate']
            line_dict['start_date'] = line_das['Start Date']
            line_dict['end_date'] = line_das['End Date']
            line_dict['goal'] = line_das[das_month]

            ##################################################################################
            # Select data
            ##################################################################################

            line_delivery = mini_delivery[mini_delivery['Line Description'] == line_dict['name']]
            line_site_goals = mini_site_goals[mini_site_goals['Line Description'] == line_dict['name']]
            line_third_party_imps = mini_third_party_imps[
                mini_third_party_imps['Line Description'] == line_dict['name']]

            has_third_party_imps = False
            if (line_dict['type'] == 'CPM') and (line_third_party_imps['3rd Party'].sum() > 0):
                has_third_party_imps = True

            ##################################################################################
            # Format delivery
            ##################################################################################

            # Initialize
            line_dict['delivery'] = None
            line_dict['delivery_sum'] = None

            if line_delivery['Impressions/UVs'].sum() > 0:

                # 1. Daily all1 total
                daily_all1_total = line_delivery[['Date', 'Impressions/UVs']].groupby(
                    'Date').sum().reset_index().rename(columns={'Impressions/UVs': 'DFP'})

                # 2. Daily site total
                daily_site_total = line_delivery[['Date', 'Site', 'Impressions/UVs']]
                daily_site_total = pd.pivot_table(daily_site_total, index='Date', columns=['Site'],
                                                  values='Impressions/UVs', fill_value=0, aggfunc=np.sum)

                daily_site_total_rename_dict = {}
                for col in daily_site_total.columns.tolist():
                    daily_site_total_rename_dict[col] = '* ' + col
                daily_site_total = daily_site_total.rename(columns=daily_site_total_rename_dict).reset_index()

                # 3. Daily size total for each site
                daily_size_site_total = line_delivery[['Date', 'site_size', 'Impressions/UVs']]
                daily_size_site_total = pd.pivot_table(daily_size_site_total, index='Date', columns=['site_size'],
                                                       values='Impressions/UVs', fill_value=0,
                                                       aggfunc=np.sum).reset_index()

                # 4. Join all
                line_delivery = pd.merge(daily_all1_total, daily_site_total, how='outer', on='Date')
                line_delivery = pd.merge(line_delivery, daily_size_site_total, how='outer', on='Date')
                if has_third_party_imps:
                    line_delivery = pd.merge(line_delivery, line_third_party_imps, how='outer', on='Date')
                line_delivery = line_delivery.fillna(0)

                # 5. Order columns
                site_sort_list = ['HL', 'Drugs.com', 'GoodRx', 'Medical News Today',
                                  'EmpowHer', 'eMedTV', 'Black Health Matters',
                                  'Livestrong', 'eHow', 'Dr.Gourmet']

                new_columns = ['Date', 'DFP']
                columns = line_delivery.columns.tolist()
                columns.remove('Date')
                columns.remove('DFP')
                if has_third_party_imps:
                    new_columns = ['Date', '3rd Party', 'DFP']
                    columns.remove('3rd Party')
                for site in site_sort_list:
                    site_sizes = []
                    site_total = []
                    for col in columns:
                        if site_abbr_dict[site] in col:
                            if col.startswith('*'):
                                site_total.append(col)
                            else:
                                site_sizes.append(col)
                    if line_dict['type'] == 'CPUV':
                        new_columns += site_total
                    else:
                        new_columns += sorted(site_sizes) + site_total
                line_delivery = line_delivery[new_columns]

                # 6. Add to dictionary
                line_delivery['Date'] = [str(d) for d in line_delivery[
                    'Date']]  # Need this. Otherwise the Date column will be missing in the sum
                line_dict['delivery'] = line_delivery
                line_dict['delivery_sum'] = line_delivery.sum(axis=0)

            ##################################################################################
            # Site goal and discrepancy
            ##################################################################################

            line_site_goals_dict = {}
            for j in range(len(line_site_goals)):
                per_site = line_site_goals.iloc[j]
                line_site_goals_dict[per_site['Site']] = (per_site['Site Goal'], per_site['MTD Disc'])
            line_dict['site_goals'] = line_site_goals_dict

            ##################################################################################
            # Hit the goal
            ##################################################################################

            if line_dict['delivery'] is None:
                first_party_total = 0
                aim_towards = line_dict['goal']
                line_dict['hit_goal'] = 0
            else:
                first_party_total = daily_all1_total['DFP'].sum()
                if 'HL' in line_site_goals_dict:
                    overall_disc = line_site_goals_dict['HL'][1]
                else:
                    overall_disc = 0.0
                aim_towards = line_dict['goal'] / (1 - overall_disc)
                if first_party_total >= aim_towards:
                    line_dict['hit_goal'] = 1
                else:
                    line_dict['hit_goal'] = 0

            ##################################################################################
            # Pacing based on daily average needed
            ##################################################################################

            line_start_date = line_dict['start_date']
            if line_start_date < month_start:
                line_start_date = month_start
            line_end_date = line_dict['end_date']
            if line_end_date > month_end:
                line_end_date = month_end

            n_days_this_month = line_end_date.day - line_start_date.day + 1
            n_days_passed = last_delivery_date.day - line_start_date.day + 1
            
            if n_days_passed <= 0:
                line_dict['pacing_daily_ave'] = 0
            else:
                line_dict['pacing_daily_ave'] = first_party_total / (1.0 * aim_towards / n_days_this_month * n_days_passed)

            ##################################################################################
            # Pacing group based on daily average needed
            ##################################################################################

            pacing = line_dict['pacing_daily_ave']
            line_dict['pacing_daily_ave_group'] = 'onpace'
            if pacing <= 0.85:
                line_dict['pacing_daily_ave_group'] = 'cold'
            elif pacing >= 1.25:
                line_dict['pacing_daily_ave_group'] = 'hot'

            ##################################################################################
            # Pacing based on yesterday's delivery
            ##################################################################################

            n_days_left = line_end_date.day - last_delivery_date.day

            if line_dict['delivery'] is None:
                line_dict['pacing_yesterday'] = None
            elif n_days_left > 0:
                list_first_party_yesterday = daily_all1_total[daily_all1_total['Date'] == last_delivery_date][
                    'DFP'].tolist()
                if len(list_first_party_yesterday) == 1:
                    first_party_yesterday = list_first_party_yesterday[0]
                    first_party_need_per_day = 1.0 * (aim_towards - first_party_total) / n_days_left
                    if first_party_need_per_day == 0:
                        line_dict['pacing_yesterday'] = None
                    else:
                        line_dict['pacing_yesterday'] = first_party_yesterday / first_party_need_per_day
                else:
                    line_dict['pacing_yesterday'] = None
            else:
                line_dict['pacing_yesterday'] = None

            ##################################################################################
            # Pacing group based on yesterday's delivery
            ##################################################################################

            pacing = line_dict['pacing_yesterday']

            if line_dict['hit_goal'] == 1:
                line_dict['pacing_yesterday_group'] = 'onpace'
            elif pacing is None:
                line_dict['pacing_yesterday'] = 0
                line_dict['pacing_yesterday_group'] = 'cold'
            elif pacing <= 0.85:
                line_dict['pacing_yesterday_group'] = 'cold'
            elif pacing >= 1.25:
                line_dict['pacing_yesterday_group'] = 'hot'
            else:
                line_dict['pacing_yesterday_group'] = 'onpace'

            ##################################################################################
            # Misc.
            ##################################################################################

            line_dict['n_days_till_end'] = n_days_left
            line_dict['n_days_till_25'] = 25 - last_delivery_date.day

            return line_dict

        for i in range(len(mini_das)):
            line_dict_list.append(get_line_dict(mini_das.iloc[i]))

        campaign_dict['line_dict_list'] = line_dict_list

        ##################################################################################
        # Count of lines, hit goal and pacing
        ##################################################################################

        campaign_dict['hit_goal'] = [0, 0]  # hit goal, total
        campaign_dict['pacing_list'] = [0, 0, 0]  # hot, onpace, cold

        for line_dict in line_dict_list:
            # Hit goal
            campaign_dict['hit_goal'][1] += 1
            if line_dict['hit_goal'] == 1:
                campaign_dict['hit_goal'][0] += 1

            # Count of pacing group
            pacing_group = line_dict['pacing_yesterday_group']
            if pacing_group == 'hot':
                campaign_dict['pacing_list'][0] += 1
            elif pacing_group == 'onpace':
                campaign_dict['pacing_list'][1] += 1
            elif pacing_group == 'cold':
                campaign_dict['pacing_list'][2] += 1

        return campaign_dict

    bbr_list = das['BBR'].drop_duplicates().tolist()
    for bbr in bbr_list:
        campaign_dict_list.append(get_campaign_dict(bbr))
    
    return (campaign_dict_list, last_delivery_date)

############################################################################
# Make a campaign html
############################################################################

def get_line_info(line_dict):
    """Return a string to be displayed in a line item header."""
 
    # 1. Stage
    line_info = line_dict['stage']

    # 2. Price type
    line_info += ' | ' + line_dict['type']

    # 3. Rate
    if line_dict['prod_rate'] == 0:
        line_info += ' $' + '{0:.2f}'.format(line_dict['base_rate'])
    else:
        line_info += ' $' + '{0:.2f}'.format(line_dict['base_rate'] + line_dict['prod_rate'])
        line_info += ' ($' + '{0:.2f}'.format(line_dict['base_rate']) + ' + $' + '{0:.2f}'.format(line_dict['prod_rate']) + ')'

    # 4. Viewability guarantee
    if line_dict['v_guarantee'] != 'N/A':
        if line_dict['v_guarantee'] > 0.0:
            line_info += ' | ' + str(int(line_dict['v_guarantee'])) + '% viewability guarantee (' + line_dict['v_source'] + ')'

    # 5. DA/IAS blocking
    if line_dict['blocking'] not in ['N/A', 'None']:
        line_info += ' | ' + line_dict['blocking'] + ' blocking'

    # 6. Start date, end date
    line_info += ' | ' + line_dict['start_date'].strftime('%m/%d/%y') + ' > ' + line_dict['end_date'].strftime('%m/%d/%y')

    return line_info

def get_values_sum_top(header, values_sum):
    """Return a list of MTD delivery total. One element pre column."""

    values_sum_top = []

    for i in range(len(header)):
        col = header[i]
        sum_top = ''
        if (col in ['Date', '3rd Party', 'DFP']) | (col.startswith('*')):
            sum_top = values_sum[i]
        values_sum_top.append(sum_top)

    return values_sum_top

def get_goals_discs_aims(header, overall_goal, site_goals):
    """Return 3 lists: goal, MTD discrepancy, and aim towards. One element per column."""

    goals = []
    discs = []
    aims = []

    for col in header:
        goal = ''
        disc = ''
        aim = ''
        if col == 'DFP':
            goal = overall_goal
            if 'HL' in site_goals:
                disc = site_goals['HL'][1]
            else:
                disc = 0.0
        elif col.startswith('*'):
            site = col[2:]
            if site in site_goals:
                goal, disc = site_goals[site]
        if not isinstance(goal, str):
            aim = goal / (1 - disc)
        goals.append(goal)
        discs.append(disc)
        aims.append(aim)

    goals[0] = 'Goal'
    discs[0] = 'MTD Disc'
    aims[0] = 'Aim Towards'

    return (goals, discs, aims)

def get_lefts(aims, values_sum_top):
    """Return a list of # of imps left till hitting the goal. One element pre column."""

    lefts = []

    for i in range(len(aims)):
        aim = aims[i]
        left = ''
        if not isinstance(aim, str):
            left = aim - values_sum_top[i]
        lefts.append(left)

    lefts[0] = 'Left'

    return lefts

def get_needs_daily_end_n_25(lefts, n_days_till_end, n_days_till_25):
    """Return 2 lists: # of imps needed per day to hit the goal by the EOM, and by the 25th. One element per column."""

    needs_daily_end = []
    needs_daily_25 = []

    for left in lefts:
        need_end = ''
        need_25 = ''
        if not isinstance(left, str):
            if n_days_till_end > 0:
                need_end = left / n_days_till_end
            else:
                need_end = 935
            if n_days_till_25 > 0:
                need_25 = left / n_days_till_25
            else:
                need_25 = 935
            if need_end < 0:
                need_end = 0
            if need_25 < 0:
                need_25 = 0
        needs_daily_end.append(need_end)
        needs_daily_25.append(need_25)

    needs_daily_end[0] = 'Need daily by EOM'
    needs_daily_25[0] = 'Need daily by 25th'

    return (needs_daily_end, needs_daily_25)

def get_yesterday_pacing_end_n_25(goals, values, last_delivery_date,
                                  needs_daily_end, needs_daily_25):
    """Return 2 lists: pacing based on yesterday's delivery if end date is set to the EOM, and to the 25th. One element per column."""

    pacing_yesterday_end = []
    pacing_yesterday_25 = []

    for i in range(len(goals)):
        pacing_end = ''
        pacing_25 = ''
        if not isinstance(goals[i], str):
            yesterday_date = values[-1][0]
            yesterday_date = datetime.strptime(yesterday_date, '%Y-%m-%d').date()
            if yesterday_date == last_delivery_date:
                yesterday_delivery = values[-1][i]
            else:
                yesterday_delivery = 0
            need_end = needs_daily_end[i]
            need_25 = needs_daily_25[i]
            if need_end > 0:
                pacing_end = 1.0 * yesterday_delivery / need_end
            if need_25 > 0:
                pacing_25 = 1.0 * yesterday_delivery / need_25
        pacing_yesterday_end.append(pacing_end)
        pacing_yesterday_25.append(pacing_25)

    pacing_yesterday_end[0] = 'Yesterday Pacing by EOM'
    pacing_yesterday_25[0] = 'Yesterday Pacing by 25th'

    return (pacing_yesterday_end, pacing_yesterday_25)

def make_pacing_color_list(pacing_list, need_daily_list):
    """Return a list of strings indicating pacing, to be used for adding css class. One element per column."""

    color_list = [None] * len(pacing_list)

    for i in range(len(pacing_list)):
        pacing = pacing_list[i]
        need_daily = need_daily_list[i]
        if need_daily == 0:
            color_list[i] = 'hit_goal'
        elif not isinstance(pacing, str):
            if pacing <= 0.85:
                color_list[i] = 'cold'
            elif pacing >= 1.25:
                color_list[i] = 'hot'
            else:
                color_list[i] = 'onpace'

    return color_list

def make_last_day_color_list(values_sum_top, type, goals, aims):
    """Return a list of 'hit_goal' or None, to be used for adding css class. One element per column."""

    color_last_day = [None] * len(values_sum_top)

    for i in range(len(values_sum_top)):
        value = values_sum_top[i]
        if isinstance(value, str):
            continue
        if type == 'CPUV':
            goal_or_aim = goals[i]
        else:
            goal_or_aim = aims[i]
        if isinstance(goal_or_aim, str):
            continue
        if value >= goal_or_aim:
            color_last_day[i] = 'hit_goal'

    return color_last_day

def int_format(x):
    """Return the integer part of a number. No change to a string."""

    if isinstance(x, str):
        return x
    else:
        return '{:,}'.format(int(x))

def percent_format_1(x):
    """Return a percent-formatted number with 1 decimal place."""

    if isinstance(x, str):
        return x
    else:
        return '{0:.1f}%'.format(round(x * 100, 1))

def percent_format_int(x):
    """Return a percent-formatted number with no decimal place."""

    if isinstance(x, str):
        return x
    else:
        return str(int(round(x * 100))) + '%'

def get_col_label_list(header):
    """Return a list of strings that indicate what kind of column it is, to be used as css class. One element per column."""

    col_label_list = []

    def extract_site_abbr(col):
        site_abbr = col.replace('*', '').strip().split(' ')[0].replace('.', '')
        return 'col_site_' + site_abbr.lower()

    for col in header:
        if col in ['Date', '3rd Party', 'DFP', 'Total']:
            col_label_list.append('li_col_all')
        elif col.startswith('*'):
            col_label_list.append('li_col_site_total' + ' ' + extract_site_abbr(col))
        else:
            col_label_list.append('li_col_site_size' + ' ' + extract_site_abbr(col))

    return col_label_list

def make_ab_campaign_html(campaign_dict, last_delivery_date, non_html, output_folder_name):
    """Create and save an html file for a specified campaign."""

    doc, tag, text = Doc().tagtext()

    with tag('html'):
        with tag('head'):
            doc.stag('link', rel='stylesheet', type='text/css', href=non_html['css'])
            doc.stag('link', rel='stylesheet', type='text/css', href=non_html['jqui css'])

        with tag('body'):
            ############################################################################
            # Menu
            ############################################################################

            with tag('div', id='campaign_html_menu'):
                with tag('a', href='index.html'):
                    text('Index')
                with tag('span'):
                    text('|')
                with tag('a', href='', download=''):
                    text('Download')

            ############################################################################
            # Campaign Info
            ############################################################################

            with tag('div', id='camp_header'):
                with tag('h1'):
                    text(campaign_dict['name'] + ' (BBR #' + campaign_dict['bbr'] + ')')
                with tag('h3'):
                    text('CM: ' + campaign_dict['cm'] + ' | AM: ' + campaign_dict['am'])

            ############################################################################
            # Line Items
            ############################################################################

            with tag('div', id='camp_details'):
                for line_dict in campaign_dict['line_dict_list']:

                    ############################################################################
                    # Line Item Info
                    ############################################################################
                    
                    line_item_header_klass = 'li_header'
                    if line_dict['hit_goal'] == 1:
                        line_item_header_klass += ' ' + 'li_header_hit_goal'

                    with tag('div', klass=line_item_header_klass):
                        with tag('h2'):
                            text('#' + str(int(line_dict['num'])) + ' ' + line_dict['name'] + ' (' + line_dict['oli'] + ')')
                       
                        ###TESTING###
                        print(campaign_dict['name'], line_dict['name'])
                        print('pacing yesterday', line_dict['pacing_yesterday'])
                        print('pacing daily ave', line_dict['pacing_daily_ave'])
                        #############
 
                        pacing_yesterday = line_dict['pacing_yesterday']
                        if pacing_yesterday is not None:
                            pacing_yesterday = int(round(pacing_yesterday * 100))
                        pacing_mtd = int(round(line_dict['pacing_daily_ave'] * 100))

                        with tag('h4'):
                            if line_dict['hit_goal'] != 1:
                                with tag('span', klass='li_header_' + line_dict['pacing_yesterday_group']):
                                    text(str(pacing_yesterday) + '% (yesterday)')
                                text(' | ')
                            with tag('span', klass='li_header_' + line_dict['pacing_daily_ave_group']):
                                text(str(pacing_mtd) + '% (mtd)')
                            text(' | ')
                            text(get_line_info(line_dict))

                    ############################################################################
                    # Line Item Table
                    ############################################################################
                    
                    if line_dict['delivery'] is not None:

                        ############################################################################
                        # Values
                        ############################################################################

                        header = line_dict['delivery'].columns.tolist()
                        values = line_dict['delivery'].values.tolist()
                        values_sum = line_dict['delivery_sum'].tolist()
                        values_sum[0] = 'MTD'
                        values_sum_top = get_values_sum_top(header, values_sum)

                        overall_goal = line_dict['goal']
                        site_goals = line_dict['site_goals']
                        goals, discs, aims = get_goals_discs_aims(header, overall_goal, site_goals)
                        lefts = get_lefts(aims, values_sum_top)

                        n_days_till_end = line_dict['n_days_till_end']
                        n_days_till_25 = line_dict['n_days_till_25']
                        needs_daily_end, needs_daily_25 = get_needs_daily_end_n_25(lefts, n_days_till_end, n_days_till_25)
                        pacing_yesterday_end, pacing_yesterday_25 = get_yesterday_pacing_end_n_25(goals, values, last_delivery_date, needs_daily_end, needs_daily_25)

                        ############################################################################
                        # Colors
                        ############################################################################

                        color_by_pacing_end = make_pacing_color_list(pacing_yesterday_end, needs_daily_end)
                        color_by_pacing_25 = make_pacing_color_list(pacing_yesterday_25, needs_daily_25)

                        type = line_dict['type']
                        color_last_day = make_last_day_color_list(values_sum_top, type, goals, aims)

                        ############################################################################
                        # Convert values to string for html
                        ############################################################################

                        values = [list(map(int_format, v)) for v in values]
                        values_sum = list(map(int_format, values_sum))
                        values_sum_top = list(map(int_format, values_sum_top))

                        goals = list(map(int_format, goals))
                        discs = list(map(percent_format_1, discs))
                        aims = list(map(int_format, aims))
                        lefts = list(map(int_format, lefts))

                        needs_daily_end = list(map(int_format, needs_daily_end))
                        needs_daily_25 = list(map(int_format, needs_daily_25))
                        pacing_yesterday_end = list(map(percent_format_int, pacing_yesterday_end))
                        pacing_yesterday_25 = list(map(percent_format_int, pacing_yesterday_25))

                        # Change DFP to Total for CPUV
                        if type == 'CPUV':
                            header[header.index('DFP')] = 'Total'

                        ############################################################################
                        # List of what'll go into table
                        ############################################################################

                        month_end = start_end_month(last_delivery_date)[1]

                        if last_delivery_date.day < month_end.day:
                            if type == 'CPUV':
                                above_header = [(pacing_yesterday_end, color_by_pacing_end),
                                                values_sum_top,
                                                goals]
                                below_delivery = [(needs_daily_end, color_by_pacing_end), values_sum, lefts]
                            else:
                                above_header = [(pacing_yesterday_end, color_by_pacing_end),
                                                (pacing_yesterday_25, color_by_pacing_25),
                                                values_sum_top,
                                                aims,
                                                discs,
                                                goals]
                                below_delivery = [(needs_daily_end, color_by_pacing_end),
                                                  (needs_daily_25, color_by_pacing_25),
                                                  values_sum,
                                                  lefts]
                                if last_delivery_date.day >= 25:
                                    above_header.pop(1)
                                    below_delivery.pop(1)
                        else:
                            if type == 'CPUV':
                                above_header = [(values_sum_top, color_last_day), goals]
                            else:
                                above_header = [(values_sum_top, color_last_day), aims, discs, goals]
                            below_delivery = [(values_sum, color_last_day), lefts]

                        ############################################################################
                        # Let's go!
                        ############################################################################

                        col_label_list = get_col_label_list(header)

                        def add_header_row():
                            with tag('tr'):
                                for i in range(len(header)):
                                    col = header[i]
                                    if (col in ['Date', '3rd Party', 'DFP', 'Total']) | (col.startswith('*')):
                                        klass = 'not_regular' + ' ' + col_label_list[i]
                                    else:
                                        klass = 'regular' + ' ' + col_label_list[i]
                                    with tag('th', klass=klass):
                                        text(col)

                        def add_rows(list_of_list):
                            for row in list_of_list:
                                if isinstance(row, tuple):
                                    row_content = row[0]
                                    row_color = row[1]
                                else:
                                    row_content = row
                                    row_color = [None] * len(row_content)
                                with tag('tr'):
                                    for ith_cell in range(len(row_content)):
                                        cell_content = row_content[ith_cell]
                                        cell_color = row_color[ith_cell]
                                        klass = col_label_list[ith_cell]
                                        if cell_color is not None:
                                            klass += ' ' + cell_color
                                        if ith_cell == 0:
                                            with tag('th', klass=klass):
                                                text(cell_content)
                                        else:
                                            with tag('td', klass=klass):
                                                text(cell_content)

                        with tag('div', klass='li_details', style='overflow-x:auto;'):
                            with tag('table'):
                                add_rows(above_header)
                                add_header_row()
                                add_rows(values)
                                add_header_row()
                                add_rows(below_delivery)
                    else:
                        with tag('div', klass='li_details'):
                            text('No delivery so far.')

            ############################################################################
            # Javascript
            ############################################################################
            
            with tag('script', src='https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js'):
                pass
            with tag('script', type='text/javascript', src=non_html['jqui js']):
                pass
            with tag('script', type='text/javascript', src=non_html['js']):
                pass

    ############################################################################
    # Get text
    ############################################################################
    
    output = indent(doc.getvalue())

    ############################################################################
    # Write to file
    ############################################################################
    
    file_path = output_folder_name + '/' + campaign_dict['name'].replace(' ', '_') + '.html'
    with open(file_path, 'w') as f:
        f.write(output)

    return

############################################################################
# Make index html
############################################################################

def make_ab_index_html(campaign_dict_list, non_html, output_folder_name):
    """Create and save an index html file."""

    ############################################################################
    # Prep
    ############################################################################

    camp = {}
    for campaign_dict in campaign_dict_list:
        camp[campaign_dict['name']] = {'cms': campaign_dict['cm'], 
                                       'hit_goal': campaign_dict['hit_goal'], 
                                       'pacing_list': campaign_dict['pacing_list']}

    ############################################################################
    # List of CMs
    ############################################################################
    
    cm_list = []
    for name in camp:
        cms = camp[name]['cms'].split(', ')
        for cm in cms:
            cm_list.append(cm)
    cm_list = sorted(list(set(cm_list)))

    cm_name2index = {}
    for i in range(len(cm_list)):
        cm_name2index[cm_list[i]] = 'cm' + str(i+1)

    ############################################################################
    # Main
    ############################################################################

    doc, tag, text = Doc().tagtext()

    with tag('html'):
        with tag('head'):
            doc.stag('link', rel='stylesheet', type='text/css', href=non_html['css'])
            doc.stag('link', rel='stylesheet', type='text/css', href=non_html['jqui css'])

        with tag('body'):
            with tag('select', id='select_cm'):
                with tag('option', value="all_cms", selected="selected"):
                    text('All CMs')
                for cm in cm_list:
                    with tag('option', value=cm_name2index[cm]):
                        text(cm)

            with tag('select', id='select_pacing'):
                with tag('option', value='all_pacing', selected='selected'):
                    text('All Pacing')
                with tag('option', value='pacing_cold'):
                    text('Cold')
                with tag('option', value='on_pace'):
                    text('On Pace')
                with tag('option', value='pacing_hot'):
                    text('Hot')

            with tag('div', id='main'):
                for name in sorted(list(camp.keys())):

                    ############################################################################
                    # Add CM label
                    ############################################################################

                    cms = camp[name]['cms']

                    cm_index_list = []
                    for cm in cms.split(', '):
                        cm_index_list.append(cm_name2index[cm])
                    campaign_klass = ' '.join(cm_index_list)

                    ############################################################################
                    # Add Hit goal label
                    ############################################################################

                    n_li_hit_goal, n_li_all = camp[name]['hit_goal']

                    n_li_hit_goal_klass = 'index_n_hit_goal'
                    if n_li_hit_goal != n_li_all:
                        n_li_hit_goal_klass += ' ' + 'notall'

                    ############################################################################
                    # Add Pacing label
                    ############################################################################

                    n_li_hot, n_li_onpace, n_li_cold = camp[name]['pacing_list']

                    if n_li_hot > 0:
                        campaign_klass += ' ' + 'pacing_hot'
                    if n_li_onpace > 0:
                        campaign_klass += ' ' + 'on_pace'
                    if n_li_cold > 0:
                        campaign_klass += ' ' + 'pacing_cold'

                    ############################################################################
                    # Let's go!
                    ############################################################################

                    with tag('div', klass=campaign_klass):
                        with tag('span', klass=n_li_hit_goal_klass):
                            text(str(n_li_hit_goal) + ' of ' + str(n_li_all))
                        with tag('span', klass='index_n_hot'):
                            text(str(n_li_hot))
                        with tag('span', klass='index_n_onpace'):
                            text(str(n_li_onpace))
                        with tag('span', klass='index_n_cold'):
                            text(str(n_li_cold))
                        with tag('a', href=name.replace(' ', '_') + '.html', target='iframe_content'):
                            text(name)

            ############################################################################
            # Javascript
            ############################################################################

            with tag('script', src='https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js'):
                pass
            with tag('script', type='text/javascript', src=non_html['jqui js']):
                pass
            with tag('script', type='text/javascript', src=non_html['js']):
                pass

    ############################################################################
    # Get text
    ############################################################################

    output = indent(doc.getvalue())

    ############################################################################
    # Write to file
    ############################################################################

    file_path = output_folder_name + '/' + 'index.html'
    with open(file_path, 'w') as f:
        f.write(output)

############################################################################
# Make iframes html
############################################################################

def make_ab_iframes_html(non_html, output_folder_name):
    """Create and save a home html file, the one with 2 iframes."""

    doc, tag, text = Doc().tagtext()

    with tag('html'):
        with tag('head'):
            doc.stag('link', rel='stylesheet', type='text/css', href=non_html['css'])
            doc.stag('link', rel='stylesheet', type='text/css', href=non_html['jqui css'])

        with tag('body'):
            with tag('div', id='iframes_wrapper'):
                with tag('div', id='iframe_left_wrapper'):
                    with tag('iframe', id='iframe_left', src='index.html', name='iframe_index'):
                        pass
                with tag('div', id='iframe_right_wrapper'):
                    with tag('iframe', id='iframe_right', src='https://www.google.com/', name='iframe_content'):
                        pass
            with tag('script', src='https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js'):
                pass
            with tag('script', type='text/javascript', src=non_html['jqui js']):
                pass
            with tag('script', type='text/javascript', src=non_html['js']):
                pass

    ############################################################################
    # Get text
    ############################################################################

    output = indent(doc.getvalue())

    ############################################################################
    # Write to file
    ############################################################################

    file_path = output_folder_name + '/' + 'home.html'
    with open(file_path, 'w') as f:
        f.write(output)
