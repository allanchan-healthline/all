from NEW_helpers import *

###################################################################
folder_id = '0B71ox_2Qc7gmLW54VlhUeHZ6cGc'
###################################################################

file_list = gdrive_get_file_info_list(folder_id)
for file in file_list:
    delete_in_gdrive(file['id'])
