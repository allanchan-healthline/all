import sys

from path2pickles import *
from report_helpers import *

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
    with open(DIR_PICKLES + '/' + 'add_special_case.pickle', 'rb') as f:
        add_special_case = pickle.load(f)

    ############################################################################
    # Main
    ############################################################################

    daily_site_report = get_daily_site_report(all1, site_goals)
    das_aggregated_dict = get_das_aggregated_dict(daily_site_report, add_special_case)

    up_das_agg2gsheet(das_aggregated_dict)
    up_das_agg2gdrive(das_aggregated_dict['per site & placement'])

if __name__ == '__main__':
    year = int(sys.argv[1])
    mo = int(sys.argv[2])
    main(year, mo)
