from path2pickles import *
from NEW_helpers import *
from gsheet_gdrive_api import *

import os
import shutil
import time
import pickle
import time

import requests

import dfareporting_utils
from oauth2client import client
import googleapiclient

from googleads import dfp
from googleads import errors

import pandas as pd
import csv
import re
import openpyxl as opx
from datetime import datetime, date

import pytz
from pytz import timezone

pd.options.mode.chained_assignment = None  # default='warn'


#####################################################
# Monthly DCM Reports, YTD, for BizOps
# start_date, end_date in the form of 'yyyy-mm-dd'
#
#Campaign    
#Campaign ID    
#Placement    
#Placement ID    
#Month    
#Placement Cost Structure    
#Placement Pixel Size    
#Placement Rate    
#Platform Type    
#Package/Roadblock    
#Package/Roadblock ID    
#Impressions    
#Clicks
######################################################

def ytd_monthly_dcm_reporting_4bizops(start_date, end_date):

    DIR_PICKLES = DIR_PICKLES_ADP
    check_and_make_dir(DIR_PICKLES)

    # Check if a pickle file exists.
    pickle_file_name = 'ytd_monthly_dcm_reporting_4bizops' + start_date + '_' + end_date + '.pickle'
    if os.path.exists(DIR_PICKLES + '/' + pickle_file_name):
        with open(DIR_PICKLES + '/' + pickle_file_name, 'rb') as f:
            return pickle.load(f)

    ######################################################

    output_folder_name = 'YTD Monthly DCM Reports 4BizOps'
    if os.path.exists(output_folder_name):
        shutil.rmtree(output_folder_name)
    os.makedirs(output_folder_name)

    ##0. Prep
    service = dfareporting_utils.setup(None)

    report = {
        'name': 'Test HL',
        'type': 'STANDARD',
        # 'format': 'EXCEL',
        'criteria': {
            'dateRange': {'startDate': start_date, 'endDate': end_date},
            'dimensions': [{'name': 'dfa:campaign'}, {'name': 'dfa:campaignId'},
                           {'name': 'dfa:placement'}, {'name': 'dfa:placementId'},
                           {'name': 'dfa:month'},
                           {'name': 'dfa:placementCostStructure'}, {'name': 'dfa:placementSize'}, {'name': 'dfa:placementRate'},
                           {'name': 'dfa:platformType'},
                           {'name': 'dfa:packageRoadblock'}, {'name': 'dfa:packageRoadblockId'}],
            'metricNames': ['dfa:impressions', 'dfa:clicks']
        }
    }

    ##1. Get profile id's
    print('Getting profile id\'s...')
    try:
        request = service.userProfiles().list()
        response = request.execute()

        for_df = {}
        for profile in response['items']:
            for_df[profile['profileId']] = profile
        profiles_df = pd.DataFrame(for_df).transpose()

    except client.AccessTokenRefreshError:
        print('The credentials have been revoked or expired, please re-run the application to re-authorize')

    ##2. Create a report in DCM
    print('Creating DCM reports...')
    for i, row in profiles_df.iterrows():
        profile_id = row['profileId']
        account_name = row['accountName']
        output_file_name = account_name + '_' + str(profile_id) + '_' + start_date + '_' + end_date
        output_file_name = output_file_name.replace(':', ' ')
        output_file_name = output_file_name.replace('/', '')
        output_file_name = output_file_name + '.csv'
        profiles_df.loc[profiles_df['profileId'] == profile_id, 'Output File Name'] = output_file_name

        try:
            request = service.reports().insert(profileId=profile_id, body=report)
            response = request.execute()
            report_id = response['id']
            profiles_df.loc[profiles_df['profileId'] == profile_id, 'report_id'] = report_id

        except client.AccessTokenRefreshError:
            print('The credentials have been revoked or expired, please re-run the application to re-authorize')

    ##3. Run a report
    print('Running reports...')
    for i, row in profiles_df.iterrows():
        profile_id = row['profileId']
        report_id = row['report_id']

        try:
            request = service.reports().run(profileId=profile_id, reportId=report_id)
            result = request.execute()
            file_id = result['id']
            profiles_df.loc[profiles_df['profileId'] == profile_id, 'file_id'] = file_id

        except client.AccessTokenRefreshError:
            print('The credentials have been revoked or expired, please re-run the application to re-authorize')

    ##4. Keep looping till all files are downloaded
    profiles_df['report_downloaded'] = False

    print('Downloading files...')
    j = 1
    while len(profiles_df[profiles_df['report_downloaded'] == False]) > 0:
        if j >= 20:
            print('Not all files were downloaded.')
            break

        time.sleep(5)
        print('Round ' + str(j))
        ##4.1 Get a report status
        for i, row in profiles_df.iterrows():
            time.sleep(1)

            report_downloaded = row['report_downloaded']
            profile_id = row['profileId']
            report_id = row['report_id']
            file_id = row['file_id']

            if not report_downloaded:
                try:
                    request = service.reports().files().list(profileId=profile_id, reportId=report_id)

                    while True:
                        response = request.execute()
                        for report_file in response['items']:
                            if report_file['id'] == file_id:
                                profiles_df.loc[profiles_df['profileId'] == profile_id, 'report_status'] = report_file[
                                    'status']
                                break
                        break

                except client.AccessTokenRefreshError:
                    print('The credentials have been revoked or expired, please re-run the application to re-authorize')

        ##4.2 Download a file and Delete a report
        for i, row in profiles_df.iterrows():
            report_status = row['report_status']
            report_downloaded = row['report_downloaded']

            if (report_status == 'REPORT_AVAILABLE') & (not report_downloaded):
                profile_id = row['profileId']
                report_id = row['report_id']
                file_id = row['file_id']
                output_file_name = row['Output File Name']
                account_name = row['accountName']

                ##4.2.1 Download a file
                try:
                    request = service.files().get_media(reportId=report_id, fileId=file_id)

                    f = open(os.path.join(output_folder_name, output_file_name), 'wb')
                    f.write(request.execute())
                    f.close()

                    profiles_df.loc[profiles_df['profileId'] == profile_id, 'report_downloaded'] = True

                except client.AccessTokenRefreshError:
                    print (
                    'The credentials have been revoked or expired, please re-run the application to re-authorize')

                ##4.2.2 Delete a report
                try:
                    request = service.reports().delete(profileId=profile_id, reportId=report_id)
                    request.execute()
                    print(account_name.encode('utf-8'))

                except client.AccessTokenRefreshError:
                    print('The credentials have been revoked or expired, please re-run the application to re-authorize')

                except:
                    print('Delete failed for profile ' + profile_id)

        j += 1

    ##5. Delete files with no data, and create a file with all data
    print('Finishing up...')
    all_data = pd.DataFrame()

    for i, row in profiles_df.iterrows():
        output_file_name = row['Output File Name']
        if row['report_downloaded']:
            account_id = row['accountId']

            f = open(output_folder_name + '/' + output_file_name, encoding='utf8')
            r = 0
            for line in csv.reader(f):
                if len(line) > 0:
                    if line[0] == 'Campaign':
                        f.close()
                        break
                    else:
                        r += 1
                else:
                    r += 1
            data = pd.read_csv(output_folder_name + '/' + output_file_name, skiprows=r, skipfooter=1, engine='python',
                               encoding='utf-8')
            profiles_df.loc[profiles_df['Output File Name'] == output_file_name, '# of Data Rows'] = len(data)

            if len(data) == 0:
                os.remove(output_folder_name + '/' + output_file_name)
            else:
                data['Account ID'] = int(account_id)
                all_data = all_data.append(data)
        else:
            profiles_df.loc[profiles_df['Output File Name'] == output_file_name, 'Output File Name'] = ''

    all_data = all_data.sort_values(['Campaign', 'Placement'])[
        ['Account ID', 'Campaign', 'Campaign ID', 'Placement', 'Placement ID', 'Month', 
         'Placement Cost Structure', 'Placement Pixel Size', 'Placement Rate', 
         'Platform Type', 'Package/Roadblock', 'Package/Roadblock ID', 'Impressions', 'Clicks']]

    # Dedupe all_data
    all_data = all_data.drop_duplicates()

    profiles_df = profiles_df[['accountId', 'accountName', 'profileId', 'subAccountId', 'subAccountName',
                               'userName', 'report_downloaded', '# of Data Rows',
                               'Output File Name']].sort_values('Output File Name')
    for col in ['accountId', 'profileId', 'subAccountId']:
        profiles_df[col] = [int(entry) if isinstance(entry, str) else entry for entry in profiles_df[col]]

    # Save to pickle
    with open(DIR_PICKLES + '/' + pickle_file_name, 'wb') as f:
        pickle.dump((all_data, profiles_df), f)

    return (all_data, profiles_df)


