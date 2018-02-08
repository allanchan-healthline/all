import sys
sys.path.append('/home/fouyang/ad-book/python_path')
from path2pickles import *
from NEW_helpers import *
from adbook_helpers import *

import os
import shutil
import pickle

def main(year, mo):
    """Generate adbook html files in a directory called adbook_year_mo.
    Also, copy 2 css files and 2 js files in that directory.
    """

    ############################################################################
    # Get most recent pickles
    ############################################################################

    DIR_PICKLES = PATH2PICKLES + '/' + PREFIX4ALWAYS_UP2DATE + str(year) + '_' + str(mo).zfill(2)
    with open(DIR_PICKLES + '/' + 'all1.pickle', 'rb') as f:
        all1 = pickle.load(f)
    with open(DIR_PICKLES + '/' + 'site_goals.pickle', 'rb') as f:
        site_goals = pickle.load(f)
    with open(DIR_PICKLES + '/' + 'third_party_imps.pickle', 'rb') as f:
        third_party_imps = pickle.load(f)

    ############################################################################
    # Main
    ############################################################################

    ab_campaign_dict_list, last_delivery_date = get_ab_campaign_dict_list(all1, site_goals, third_party_imps)

    output_folder_name = 'adbook_' + str(year) + '_' + str(mo).zfill(2)

    # Remove output directory if exists. Create a new one.
    if os.path.exists(output_folder_name):
        shutil.rmtree(output_folder_name)
    check_and_make_dir(output_folder_name)

    non_html = {'css': 'style.css',
                'js': 'adbook.js',
                'jqui css': 'jquery-ui-1.10.4.custom.min.css',
                'jqui js': 'jquery-ui-1.10.4.custom.min.js'}

    all_line_items_aggregation = []

    for campaign_dict in ab_campaign_dict_list:
        make_ab_campaign_html(campaign_dict, last_delivery_date, non_html, output_folder_name, all_line_items_aggregation)
    make_ab_index_html(ab_campaign_dict_list, non_html, output_folder_name)
    make_ab_iframes_html(non_html, output_folder_name)

    lineitems_revenue_aggregation = pd.concat(all_line_items_aggregation).groupby(['Date']).sum()
    daily_sum = lineitems_revenue_aggregation.sum(axis=1)
    lineitems_revenue_aggregation['Daily Sum'] = daily_sum
    aggregation_total = lineitems_revenue_aggregation.sum()
    aggregation_total = ['Total'] + pd.DataFrame(aggregation_total).transpose().applymap("${:,.2f}".format).values.tolist()[0]
    lineitems_revenue_aggregation = lineitems_revenue_aggregation.applymap("${:,.2f}".format)
    lineitems_revenue_aggregation = lineitems_revenue_aggregation.reset_index(drop=False)
    make_summary_book_html(lineitems_revenue_aggregation, non_html, output_folder_name, aggregation_total)

    for key in non_html:
        file = non_html[key]
        shutil.copyfile(file, output_folder_name + '/' + file)

    # Delete unnecessary campaigns' html files
    #keep_campaigns = list(map(lambda s: s.replace(' ', '_'), list(campaigns4index.keys())))
    #for file_name in os.listdir(output_folder_name):
    #    if file_name.replace('.html', '') not in keep_campaigns:
    #        os.remove(output_folder_name + '/' + file_name)

if __name__ == '__main__':
    year = int(sys.argv[1])
    mo = int(sys.argv[2])
    main(year, mo)
