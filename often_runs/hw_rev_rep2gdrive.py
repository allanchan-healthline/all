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
    with open(DIR_PICKLES + '/' + 'partner_capping_sp_case.pickle', 'rb') as f:
        partner_capping_sp_case = pickle.load(f)

    ############################################################################
    # Main
    ############################################################################

    now = datetime.now()

    partner_revenue_report = get_partner_revenue_report(all1, site_goals)
    daily_site_report = get_daily_site_report(all1, site_goals, partner_capping_sp_case)
    partner_revrep_check = get_partner_revrep_check(daily_site_report)

    partner_revrep2gdrive_dict = {}
    partner_revrep2gdrive_dict['file name'] = 'Partner_Revenue_Report_' + str(year) + '_' + str(mo).zfill(2)
    partner_revrep2gdrive_dict['file name'] += '_AsOf_' + now.strftime('%m-%d-%Y-%Hhr%Mmin')
    partner_revrep2gdrive_dict['file name'] += '.xlsx'
    partner_revrep2gdrive_dict['data'] = partner_revenue_report
    partner_revrep2gdrive_dict['check'] = partner_revrep_check
    up_partner_revrep2gdrive(partner_revrep2gdrive_dict)

if __name__ == '__main__':
    year = int(sys.argv[1])
    mo = int(sys.argv[2])
    main(year, mo)
