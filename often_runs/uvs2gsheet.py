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
    with open(DIR_PICKLES + '/' + 'cpuv_goals.pickle', 'rb') as f:
        cpuv_goals = pickle.load(f)

    ############################################################################
    # Main
    ############################################################################

    monthly_uvs = get_monthly_uvs(all1, cpuv_goals)

    monthly_uvs2gsheet_dict = {}    
    monthly_uvs2gsheet_dict['ss name'] = 'Monthly_UVs_' + str(year) + '_' + str(mo).zfill(2)
    monthly_uvs2gsheet_dict['content'] = monthly_uvs

    up_monthly_uvs2gsheet(monthly_uvs2gsheet_dict)

if __name__ == '__main__':
    year = int(sys.argv[1])
    mo = int(sys.argv[2])
    main(year, mo)
