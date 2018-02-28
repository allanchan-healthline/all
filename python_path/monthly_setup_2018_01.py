
MO_YEAR = (1, 2018)

MONTHLY_SHEET_NAME = {'pas': 'Jan', 'cpuv goals': 'Jan'}

UV_TRACKER_GSHEET = {'Drugs.com': '10Vc6tIivvtYjkphe8SDN5Lu4baxrh6si7H1UWHKRTAE', 
                     'HL': '1nGYK6OAhYEubaGhMn5iqP6R0vSyKGu-YH76nwWT1L90',
                     'MNT': '1nGYK6OAhYEubaGhMn5iqP6R0vSyKGu-YH76nwWT1L90'}
# Add BCO when there's a tracker (Breastcancer.org)


LS_CORRECT_RATE_DICT = {}

DRUGS_CORRECT_RATE_LIST = [('17-319', 'Toujeo', 'HL D LS m.HL m.D Sponsorship of T2D Microsite', 1.00),
                           ('17-277', 'benralizumab', 'D m.D Brand Championing (Fasenra)', 0.30)]  # Charge Flat-fee, pay CC

def TEMP_FIX_DAS4FLAT_FEE(das):
    das = das.copy()
    das.loc[(das['Brand'] == 'Ruconest') & (das['Line Description'] == 'D GRx m.D m.GRx Competitive Conquesting (Fizayr, Cinryze, Berinert, Kalbitor, Haegarda, Ruconest) [PLACEHOLDER]'), 'Base Rate'] = 4.00
    das.loc[(das['Brand'] == 'benralizumab') & (das['Line Description'] == 'D m.D Brand Championing (Fasenra)'), ('Price Calculation Type', 'Base Rate')] = ('CPUV', 1.0)
    return das

    return das

def ADD_SPECIAL_CASE(df):
    df.loc[(df['Brand'] == 'Harvoni') &
           (df['DAS Line Item Name'].str.contains('HL D LS m.HL m.D Sponsorship of Hep C Microsite')),
           'Special Case'] = 'CPM Microsite'
