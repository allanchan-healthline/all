
MO_YEAR = (3, 2018)

MONTHLY_SHEET_NAME = {'pas': 'Mar', 'cpuv goals': 'Mar'}

UV_TRACKER_GSHEET = {'Drugs.com': '1hvstKG-Z85ZQx82aC8ew4beERVEmvSqSZvMzofIyP5U',
                     'HL': '1L2Y_VXmrPV5TkKXoSFyBN8xUVK9BhygEpfkXLsBMYdw',
                     'MNT': '1L2Y_VXmrPV5TkKXoSFyBN8xUVK9BhygEpfkXLsBMYdw',
                     'BCO': '1L2Y_VXmrPV5TkKXoSFyBN8xUVK9BhygEpfkXLsBMYdw'}

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
