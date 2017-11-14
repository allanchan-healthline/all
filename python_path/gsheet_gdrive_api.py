import os

from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import httplib2
from apiclient import discovery

def get_gsheet_service():

    home_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    #########################################################################
    # If modifying these scopes, delete your previously saved credentials
    # at ~/.credentials/sheets.googleapis.com-python-quickstart.json
    SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
    CLIENT_SECRET_FILE = home_dir + '/python_path/client_secret_gsheet.json'
    APPLICATION_NAME = 'Google Sheets API Python Quickstart'
    #########################################################################

    flags = None

    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run_flow(flow, store)
        print('Storing credentials to ' + credential_path)
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    service = discovery.build('sheets', 'v4', http=http, discoveryServiceUrl=discoveryUrl, cache_discovery=False)

    return service

def get_gdrive_service():

    home_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    #########################################################################
    # If modifying these scopes, delete your previously saved credentials
    # at ~/.credentials/drive-python-quickstart.json
    SCOPES = 'https://www.googleapis.com/auth/drive'
    CLIENT_SECRET_FILE = home_dir + '/python_path/client_secret_gdrive.json'
    APPLICATION_NAME = 'Drive API Python Quickstart'
    #########################################################################

    flags = None

    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'drive-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run_flow(flow, store)
        print('Storing credentials to ' + credential_path)

    http = credentials.authorize(httplib2.Http())
    service = discovery.build('drive', 'v3', http=http, cache_discovery=False)

    return service
