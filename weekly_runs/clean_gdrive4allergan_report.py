from NEW_helpers import *
import re

###################################################################
folder_id = '0B71ox_2Qc7gmSS1fbUJKTXEyams'
###################################################################

list_per_month = {}
pattern = re.compile('allergan_report_[0-9]{8}_[0-9]{8}')

file_list = gdrive_get_file_info_list(folder_id)
for file in file_list:
    id = file['id']
    name = file['name']
    if pattern.match(name):
        report_year_mo = name[:24]
        if report_year_mo in list_per_month:
            list_per_month[report_year_mo].append((id, name))
        else:
            list_per_month[report_year_mo] = [(id, name)]

for report_year_mo in list_per_month:
    list_per_month[report_year_mo].sort(key=lambda x: x[1], reverse=True)
    for i in range(len(list_per_month[report_year_mo])):
        if i < 1:
            continue
        file_id = list_per_month[report_year_mo][i][0]
        delete_in_gdrive(file_id)
