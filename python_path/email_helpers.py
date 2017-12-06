from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib

def email2adops_over_threshold_last_hour(df, csv_file, threshold=50000):

    ##########################################################################
    e_address = 'adopssf@healthline.com'
    password = 'healthline15'
    ##########################################################################

    df2email = df[df['Ad Server Impressions'] > threshold]
    if len(df2email) == 0:  # Done if no line is over threshold
        return

    # Prep email body
    text = ''
    for i in range(len(df2email)):
        row = df2email.iloc[i]
        order = row['Order']
        li = row['Line item']
        imp = '{:,} impressions'.format(row['Ad Server Impressions'])
        text += '\n'.join([order, li, imp]) + '\n\n'

    # Prep attachment csv
    with open(csv_file, 'r') as f:
        attachment = MIMEText(f.read())
    attachment.add_header('Content-Disposition', 'attachment', filename=csv_file)

    # Compose email
    msg = MIMEMultipart()
    msg['From'] = e_address
    msg['To'] = e_address
    msg['Subject'] = 'Check DFP Line Items: Over {}k Last Hour'.format(threshold/1000)
    msg.attach(MIMEText(text, 'plain'))
    msg.attach(attachment)

    # Send email
    smtp = smtplib.SMTP('smtp.gmail.com', 587)
    smtp.starttls()  # Tell Gmail that we want our connection to be encrypted using TLS
    smtp.login(e_address, password)
    smtp.sendmail(e_address, e_address, msg.as_string())  # from, to, email
    smtp.quit()
