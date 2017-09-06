import sys
from path2pickles import *
from NEW_helpers import *

def main(year, mo):

    # Last run
    path_last_run = 'last_run_' + str(year) + '_' + str(mo).zfill(2)
    last_run = get_last_modified_local(path_last_run)
    if last_run is None:
        exit(7)    
 
    # Most recent all1, site goals, and 3rd party imps
    DIR_PICKLES = PATH2PICKLES + '/' + PREFIX4ALWAYS_UP2DATE + str(year) + '_' + str(mo).zfill(2)
    path_all1 = DIR_PICKLES + '/' + 'all1.pickle'
    path_site_goals = DIR_PICKLES + '/' + 'site_goals.pickle'
    path_3rd_party_imps = DIR_PICKLES + '/' + 'third_party_imps.pickle'

    last_updated_all1 = get_last_modified_local(path_all1)
    last_updated_site_goals = get_last_modified_local(path_site_goals)
    last_updated_3rd_party_imps = get_last_modified_local(path_3rd_party_imps)

    if last_run < max([last_updated_all1, last_updated_site_goals, last_updated_3rd_party_imps]):
        exit(7)

if __name__ == '__main__':
    year = int(sys.argv[1])
    mo = int(sys.argv[2])
    main(year, mo)
