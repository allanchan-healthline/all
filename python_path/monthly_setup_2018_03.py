
MO_YEAR = (3, 2018)

MONTHLY_SHEET_NAME = {'pas': 'Mar', 'cpuv goals': 'Mar'}

UV_TRACKER_GSHEET = {'Drugs.com': '1op1GO2gSO47MqXR_-sMoh-0SmBuB_66Doyg9DzjY5Qo',
                     'HL': '1dZZPJGYUkBvHlavloWHA4Xw0WkbZNwyyo_GU2vyjzNA',
                     'MNT': '1dZZPJGYUkBvHlavloWHA4Xw0WkbZNwyyo_GU2vyjzNA',
                     'BCO': '1dZZPJGYUkBvHlavloWHA4Xw0WkbZNwyyo_GU2vyjzNA'}

LS_CORRECT_RATE_DICT = {}

DRUGS_CORRECT_RATE_LIST = []  # ('17-319', 'Toujeo', 'HL D LS m.HL m.D Sponsorship of T2D Microsite', 1.00)

def TEMP_FIX_DAS4FLAT_FEE(das):
    das = das.copy()
    das.loc[(das['Brand'] == 'Ruconest') & (das['Line Description'] == 'D GRx m.D m.GRx Competitive Conquesting (Fizayr, Cinryze, Berinert, Kalbitor, Haegarda, Ruconest) [PLACEHOLDER]'), 'Base Rate'] = 4.00

    return das

def ADD_SPECIAL_CASE(df):
    df.loc[(df['Brand'] == 'Harvoni') &
           (df['DAS Line Item Name'].str.contains('HL D LS m.HL m.D Sponsorship of Hep C Microsite')),
           'Special Case'] = 'CPM Microsite'
