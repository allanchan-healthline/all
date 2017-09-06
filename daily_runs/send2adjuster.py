from simple_salesforce import SalesforceLogin
import requests
import pysftp
import os

import pandas as pd
from datetime import datetime

####################################################################
username = 'kumiko.kashii@healthline.com'
password = 'Eggplant123'
security_token = 'wq3nA7vy9zD9AllhVMgMAacHQ'
####################################################################

####################################################################
# 0. Prep
####################################################################

today_date = datetime.now().date()
file_name = 'healthline_salesforce_' + str(today_date) + '.csv'
temp_file_name = 'temp_' + file_name

####################################################################
# 1. Export Ad Ops DAS Reporting from Salesforce
# Converted Report ID: 00O61000003rUoxEAE
# Non-Converted Report ID: 00O61000003KY4AEAW)
####################################################################

(session_id, instance) = SalesforceLogin(username=username, password=password, security_token=security_token)
query_url = 'https://' + instance + '/00O61000003rUox?export=1&enc=UTF-8&xf=csv'
headers = {'Content-Type': 'application/json',
           'Authorization': 'Bearer ' + session_id,
           'X-PrettyPrint': '1'}
s = requests.Session()
response = s.get(query_url, headers=headers, cookies={'sid': session_id})

with open(temp_file_name, 'wb') as f:
    f.write(response.content)

####################################################################
# 2. Clean up
####################################################################

df = pd.read_csv(temp_file_name, encoding='utf-8')

not_null_col = ['Scheduled Units', 'BBR', 'Line Item Number', 'OLI', 'Line Description']
for col in not_null_col:
    df = df[pd.notnull(df[col])]

col = ['BBR', 'Line Item Number', 'OLI', 'Line Description', 'Base Rate (converted) Currency',
       'Base Rate (converted)', 'Active Month', 'Billable Reporting Source']
df = df[col]

df.to_csv(file_name, index=False, encoding='utf-8')

####################################################################
# 3. Send to Adjuster
####################################################################

host = "ftp.ad-juster.com"
username = 'healthline'
password = 'aD6dcBKfcUuW'

cnopts = pysftp.CnOpts()
cnopts.hostkeys = None
with pysftp.Connection(host, username=username, password=password, cnopts=cnopts) as sftp:
    #dir_list = sftp.listdir()
    sftp.put(file_name, './reports' + '/' + file_name)

#for dir in dir_list:
#    print(dir)

os.remove(temp_file_name)
os.remove(file_name)

