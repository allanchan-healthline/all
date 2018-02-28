import sys

from path2pickles import *
from report_helpers import *

from datetime import datetime
import pickle

def main(year, mo):

    ############################################################################
    # Get most recent pickles
    ############################################################################

    DIR_PICKLES = PATH2PICKLES + '/' + PREFIX4ALWAYS_UP2DATE + str(year) + '_' + str(mo).zfill(2)
    with open(DIR_PICKLES + '/' + 'all1.pickle', 'rb') as f:
        all1 = pickle.load(f)
    with open(DIR_PICKLES + '/' + 'site_goals.pickle', 'rb') as f:
        site_goals = pickle.load(f)

    ############################################################################
    # Main
    ############################################################################

    now = datetime.now()

    daily_site_report = get_daily_site_report(all1, site_goals)
    daily_rev_exp = get_daily_rev_exp(daily_site_report)
    summary_by_site_dict = get_summary_by_site_dict(daily_site_report, site_goals)

    nr2gsheet_dict = {}
    nr2gsheet_dict['ss name'] = 'Network_Report_' + str(year) + '_' + str(mo).zfill(2)
    nr2gsheet_dict['rev & exp'] = daily_rev_exp
    nr2gsheet_dict['sum by site'] = summary_by_site_dict['grouped']
    up_nr2gsheet(nr2gsheet_dict)

    nr2gdrive_dict = {}
    nr2gdrive_dict['file name'] = 'NR_Data_' + str(year) + '_' + str(mo).zfill(2)
    nr2gdrive_dict['file name'] += '_AsOf_' + now.strftime('%m-%d-%Y-%Hhr%Mmin')
    nr2gdrive_dict['file name'] += '.xlsx'
    nr2gdrive_dict['daily site report'] = daily_site_report
    nr2gdrive_dict['raw summary by site'] = summary_by_site_dict['raw']
    up_nr2gdrive(nr2gdrive_dict)

if __name__ == '__main__':
    year = int(sys.argv[1])
    mo = int(sys.argv[2])
    main(year, mo)
