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

    ############################################################################
    # Main
    ############################################################################

    check_mapping_dict = get_check_mapping_dict(all1, site_goals)
    check_mapping_dict['ss name'] = 'Check_Mapping_' + str(year) + '_' + str(mo).zfill(2)
    up_check_mapping2gsheet(check_mapping_dict)

if __name__ == '__main__':
    year = int(sys.argv[1])
    mo = int(sys.argv[2])
    main(year, mo)
