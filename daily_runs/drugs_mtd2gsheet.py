from path2pickles import *
from report_helpers import *

from datetime import datetime, timedelta
import pickle

############################################################################
# Get most recent pickles
############################################################################

yesterday_date = datetime.now().date() - timedelta(days=1)
year = yesterday_date.year
mo = yesterday_date.month

DIR_PICKLES = PATH2PICKLES + '/' + PREFIX4ALWAYS_UP2DATE + str(year) + '_' + str(mo).zfill(2)
with open(DIR_PICKLES + '/' + 'all1.pickle', 'rb') as f:
    all1 = pickle.load(f)
with open(DIR_PICKLES + '/' + 'site_goals.pickle', 'rb') as f:
    site_goals = pickle.load(f)

############################################################################
# Main
############################################################################

drugs_mtd_dict = get_drugs_mtd_dict(all1, site_goals)
up_drugs_mtd(drugs_mtd_dict)


