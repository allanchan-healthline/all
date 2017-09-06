import os
import shutil
import imaplib
import email

import csv
from datetime import datetime, timedelta
import pytz

import zipfile

__author__ = 'achan@healthline.com'

def login_select_inbox():
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login('reporting@healthline.com', 'He@lthl!ne')
    mail.select()  # connect to inbox(default)
    return mail

def get_query_data(mail, sent_since, email_subject):
    query_str = '(SENTSINCE "{}") SUBJECT "{}"'.format(sent_since, email_subject)
    result, data = mail.uid('search', None, query_str)
    if len(data) == 0:
        return []
    else:
        return data[0].split()

def get_msg_datetime_in_utc(msg):
    msg_local_datetime = email.utils.parsedate_to_datetime(msg.get('date'))
    msg_utc_datetime = msg_local_datetime.astimezone(pytz.utc)
    return msg_utc_datetime

def is_newer(msg, utc_datetime):
    if get_msg_datetime_in_utc(msg) > utc_datetime:
        return True
    return False

def has_attachment(msg):
    if msg.get_content_maintype() == 'multipart':
        return True
    return False

def matches_mo_year(msg, mo_year):

    mo, year = mo_year

    # Save a temp csv file
    for part in msg.walk():
        if (type(part.get('Content-Disposition')) is str) and \
                ('attachment' in part.get('Content-Disposition').lower()):

            filename = part.get_filename()
            is_csv = True
            if not filename.endswith('.csv'):
                is_csv = False  # zip file

            if is_csv:
                with open('temp_adjuster_report.csv', 'wb') as f:
                    f.write(part.get_payload(decode=True))
            else:
                with open('temp_adjuster_report.zip', 'wb') as f:
                    f.write(part.get_payload(decode=True))
                with zipfile.ZipFile('temp_adjuster_report.zip', 'r') as zip_ref:
                    zip_ref.extractall()
                    csv_filename = zip_ref.namelist()[0]
                    if os.path.isfile('temp_adjuster_report.csv'):
                        os.remove('temp_adjuster_report.csv')
                    os.rename(csv_filename, 'temp_adjuster_report.csv')
                os.remove('temp_adjuster_report.zip')

    # Get report start date
    with open('temp_adjuster_report.csv', 'r') as f:  # default encoding is utf-8
        reader = csv.reader(f)
        for line in reader:
            if line[0] == 'Report Start:':
                report_start_date = line[1]
                break
    os.remove('temp_adjuster_report.csv')

    # Check if the report is for the given month, year
    report_mo = int(report_start_date.split('/')[0])
    report_year = int(report_start_date.split('/')[2])

    if (report_mo == mo) & (report_year == year):
        return True
    return False

def exists_new_report(sent_since_local_datetime, email_subject, mo_year):

    ########################################################################
    # Find emails
    ########################################################################

    mail = login_select_inbox()

    sent_since = sent_since_local_datetime.date() - timedelta(days=1)
    sent_since = sent_since.strftime('%d-%b-%Y')

    uid_list = get_query_data(mail, sent_since, email_subject)

    if len(uid_list) == 0:
        return False

    ########################################################################
    # Check if
    # 1. it's newer than last email
    # 2. there's an attachment
    # 3. matches month, year
    ########################################################################

    sent_since_utc_datetime = sent_since_local_datetime.astimezone(pytz.utc)

    for uid in uid_list:
        result, data = mail.uid('fetch', uid, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])

        if is_newer(msg, sent_since_utc_datetime) and has_attachment(msg) and matches_mo_year(msg, mo_year):
            return True

    return False

def get_newest_csv_filename_n_sent_local_datetime(sent_since_local_datetime, email_subject, mo_year):

    ########################################################################
    # Make a list of newer emails
    ########################################################################

    mail = login_select_inbox()

    sent_since = sent_since_local_datetime.date() - timedelta(days=1)
    sent_since = sent_since.strftime('%d-%b-%Y')

    uid_list = get_query_data(mail, sent_since, email_subject)

    ########################################################################
    # Pick newest email
    ########################################################################

    uid_datetime_list = []
    for uid in uid_list:
        result, data = mail.uid('fetch', uid, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])

        if has_attachment(msg) & matches_mo_year(msg, mo_year):
            uid_datetime_list.append((uid, get_msg_datetime_in_utc(msg)))

    uid_datetime_list.sort(key=lambda x: x[1], reverse=True)
    uid2use = uid_datetime_list[0][0]

    ########################################################################
    # Save attachment as csv
    ########################################################################

    result, data = mail.uid('fetch', uid2use, '(RFC822)')
    msg = email.message_from_bytes(data[0][1])

    msg_local_datetime = email.utils.parsedate_to_datetime(msg.get('date'))

    str_msg_local_datetime = str(msg_local_datetime.year) + str(msg_local_datetime.month).zfill(2) + str(msg_local_datetime.day).zfill(2)
    str_msg_local_datetime += '_'
    str_msg_local_datetime += str(msg_local_datetime.hour).zfill(2) + str(msg_local_datetime.minute).zfill(2)

    if 'CDR' in email_subject:
        save_as_start = 'adjuster_dfp_' + str_msg_local_datetime + '_'
    elif 'Trade Desk' in email_subject:
        save_as_start = 'adjuster_ttd_' + str_msg_local_datetime + '_'

    for part in msg.walk():
        if (type(part.get('Content-Disposition')) is str) and \
                ('attachment' in part.get('Content-Disposition').lower()):

            filename = part.get_filename()
            with open(save_as_start + filename, 'wb') as f:
                f.write(part.get_payload(decode=True))

            if filename.endswith('.csv'):
                return (save_as_start + filename, msg_local_datetime)

            if filename.endswith('.zip'):
                with zipfile.ZipFile(save_as_start + filename, 'r') as zip_ref:
                    zip_ref.extractall()
                    csv_filename = zip_ref.namelist()[0]
                    if os.path.isfile(save_as_start + csv_filename):
                        os.remove(save_as_start + csv_filename)
                    os.rename(csv_filename, save_as_start + csv_filename)
                os.remove(save_as_start + filename)
                return (save_as_start + csv_filename, msg_local_datetime)
