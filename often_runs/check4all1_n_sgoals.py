import sys
from path2pickles import *
from NEW_helpers import *

def main(year, mo):

    # Last run
    path_last_run = 'last_run_' + str(year) + '_' + str(mo).zfill(2)
    last_run = get_last_modified_local(path_last_run)
    if last_run is None:
        exit(7)    
 
    # Most recent all1 and site goals
    DIR_PICKLES = PATH2PICKLES + '/' + PREFIX4ALWAYS_UP2DATE + str(year) + '_' + str(mo).zfill(2)
    path_all1 = DIR_PICKLES + '/' + 'all1.pickle'
    path_site_goals = DIR_PICKLES + '/' + 'site_goals.pickle'

    last_updated_all1 = get_last_modified_local(path_all1)
    last_updated_site_goals = get_last_modified_local(path_site_goals)

    # Drugs IO Naming
    last_updated_drugs_io_naming = get_last_modified_gdrive('1Mx3F6K1jnf01ra2sjutmia7rMULLNlEacCcHjo98-j0')

    if last_run < max([last_updated_all1, last_updated_site_goals]):
        exit(7)
    if last_run < last_updated_drugs_io_naming:
        exit(8)  # only update Partner Rev Rep

if __name__ == '__main__':
    year = int(sys.argv[1])
    mo = int(sys.argv[2])
    main(year, mo)
