from path2pickles import *
from monthly_setup_2017_07 import TEMP_FIX_DAS4FLAT_FEE

from always_up2date_helpers import *
import pickle

mo, year = (7, 2017)

DIR_PICKLES = PATH2PICKLES + '/' + PREFIX4ALWAYS_UP2DATE + str(year) + '_' + str(mo).zfill(2)

########################################################################

with open(DIR_PICKLES + '/' + 'cpm.pickle', 'rb') as f:
    cpm = pickle.load(f)
with open(DIR_PICKLES + '/' + 'cpuv.pickle', 'rb') as f:
    cpuv = pickle.load(f)

all1 = make_all1(cpm, cpuv, TEMP_FIX_DAS4FLAT_FEE)

with open(DIR_PICKLES + '/' + 'all1.pickle', 'wb') as f:
    pickle.dump(all1, f)
