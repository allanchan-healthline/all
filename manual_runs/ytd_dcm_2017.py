from path2pickles import *
from delivery_helpers import *

import pickle

#dcm_reporting('2017-01-01', '2017-10-31')

pickle_file_name = 'dcm_reports_2017-01-01_2017-10-31.pickle'
with open(DIR_PICKLES_ADP + '/' + pickle_file_name, 'rb') as f:
    all_data, profiles_df, grouped_all_data = pickle.load(f)

file_name = 'DCM_Reports_2017-01-01_2017-10-31.xlsx'
writer = pd.ExcelWriter(file_name)
all_data.to_excel(writer, 'data', index=False)
profiles_df.to_excel(writer, 'profiles', index=False)
grouped_all_data.to_excel(writer, 'grouped', index=False)
writer.save()

folder_id = '0B71ox_2Qc7gmaGZjRjlCYjR3QXc'
save_in_gdrive(file_name, folder_id, 'application/vnd.ms-excel')

