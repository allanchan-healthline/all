from NEW_helpers import *

######################################################
folder_id = '0B71ox_2Qc7gmZDVGaHprRmQ3ajg'
######################################################

most_recent_id = gdrive_get_most_recent_file_id(folder_id)

if most_recent_id is None:
    exit()
file_info_list = gdrive_get_file_info_list(folder_id, exclude_folder=True)

for file in file_info_list:
    file_id = file['id']

    if file_id == most_recent_id:
        continue
    delete_in_gdrive(file_id)
