from NEW_helpers import *
import re

###################################################################
folder_id = '0B71ox_2Qc7gmaGZjRjlCYjR3QXc'
###################################################################

list_per_month = {}
pattern = re.compile('DCM_Reports_[0-9]{4}-[0-9]{2}-[0-9]{2}_[0-9]{4}-[0-9]{2}-[0-9]{2}\.xlsx')

file_list = gdrive_get_file_info_list(folder_id)
for file in file_list:
    id = file['id']
    name = file['name']
    last_modified = file['last_modified']
    if pattern.match(name):
        report_year_mo = name[:22]
        if report_year_mo in list_per_month:
            list_per_month[report_year_mo].append((id, name, last_modified))
        else:
            list_per_month[report_year_mo] = [(id, name, last_modified)]

for report_year_mo in list_per_month:
    list_per_month[report_year_mo].sort(key=lambda x: x[2], reverse=False)
    list_per_month[report_year_mo].sort(key=lambda x: x[1], reverse=True)
    for i in range(len(list_per_month[report_year_mo])):
        if i < 1:
            continue
        file_id = list_per_month[report_year_mo][i][0]
        delete_in_gdrive(file_id)

