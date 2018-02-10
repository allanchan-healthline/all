
MO_YEAR = (2, 2018)

MONTHLY_SHEET_NAME = {'pas': 'Feb', 'cpuv goals': 'Feb'}

UV_TRACKER_GSHEET = {'Drugs.com': '1hvstKG-Z85ZQx82aC8ew4beERVEmvSqSZvMzofIyP5U',
                     'HL': '1L2Y_VXmrPV5TkKXoSFyBN8xUVK9BhygEpfkXLsBMYdw',
                     'MNT': '1L2Y_VXmrPV5TkKXoSFyBN8xUVK9BhygEpfkXLsBMYdw',
                     'BCO': '1L2Y_VXmrPV5TkKXoSFyBN8xUVK9BhygEpfkXLsBMYdw'}

LS_CORRECT_RATE_DICT = {}

DRUGS_CORRECT_RATE_LIST = [('17-319', 'Toujeo', 'HL D LS m.HL m.D Sponsorship of T2D Microsite', 1.00),
                           ('17-277', 'benralizumab', 'D m.D Brand Championing (Fasenra)', 0.30)]  # Charge Flat-fee, pay CC

def TEMP_FIX_DAS4FLAT_FEE(das):
    das = das.copy()
    das.loc[(das['Brand'] == 'Ruconest') & (das['Line Description'] == 'D GRx m.D m.GRx Competitive Conquesting (Fizayr, Cinryze, Berinert, Kalbitor, Haegarda, Ruconest) [PLACEHOLDER]'), 'Base Rate'] = 4.00
    das.loc[(das['Brand'] == 'benralizumab') & (das['Line Description'] == 'D m.D Brand Championing (Fasenra)'), ('Price Calculation Type', 'Base Rate')] = ('CPUV', 1.0)
    return das

    return das

PARTNER_CAPPING_SP_CASE = [
    ('Drugs.com', '18-038', 'Anoro', 'D GRx m.D Competitive Conquesting (Anoro, Bevespi, Ubitron)', 5900),
    ('GoodRx', '18-038', 'Anoro', 'D GRx m.D Competitive Conquesting (Anoro, Bevespi, Ubitron)', 1825),

    ('Drugs.com', '18-025', 'Jardiance', 'D GRx m.D Competitive Conquesting (Jardiance, Januvia, Invokana)', 40898),
    ('GoodRx', '18-025', 'Jardiance', 'D GRx m.D Competitive Conquesting (Jardiance, Januvia, Invokana)', 7000),

    ('Drugs.com', '18-036', 'Kisqali', 'HL D GRx m.HL m.D m.GRX Competitive Conquesting (See List)', 5600),
    ('GoodRx', '18-036', 'Kisqali', 'HL D GRx m.HL m.D m.GRX Competitive Conquesting (See List)', 900),

    ('Drugs.com', '18-062', 'Mydayis', 'D GRx m.D Competitive Conquesting (Adderall XR, Adderall, Mydayis, non-exclusive)', 90000),
    ('GoodRx', '18-062', 'Mydayis', 'D GRx m.D Competitive Conquesting (Adderall XR, Adderall, Mydayis, non-exclusive)', 32366),

    ('Drugs.com', '18-043', 'Orencia', 'D GRx m.D m.GRx Competitive Conquesting (Orencia)', 2000),
    ('GoodRx', '18-043', 'Orencia', 'D GRx m.D m.GRx Competitive Conquesting (Orencia)', 300),

    ('Drugs.com', '18-045', 'Promacta', 'HL D GRx m.HL m.D Competitive Conquesting (Promacta, NPlate)', 1929),
    ('GoodRx', '18-045', 'Promacta', 'HL D GRx m.HL m.D Competitive Conquesting (Promacta, NPlate)', 200),

    ('Drugs.com', '17-266', 'Ruconest', 'D GRx m.D m.GRx Competitive Conquesting (Fizayr, Cinryze, Berinert, Kalbitor, Haegarda, Ruconest) [PLACEHOLDER]', 500), 
    ('GoodRx', '17-266', 'Ruconest', 'D GRx m.D m.GRx Competitive Conquesting (Fizayr, Cinryze, Berinert, Kalbitor, Haegarda, Ruconest) [PLACEHOLDER]', 500), 

    ('Drugs.com', '18-027', 'Spiriva', 'D GRx m.D m.GRx Competitive Conquesting (See List)', 4804), 
    ('GoodRx', '18-027', 'Spiriva', 'D GRx m.D m.GRx Competitive Conquesting (See List)', 1500),

    ('Drugs.com', '18-026', 'Spiriva', 'D GRx m.D GRx Competitive Conquesting (Spiriva Handihaler)', 72),
    ('GoodRx', '18-026', 'Spiriva', 'D GRx m.D GRx Competitive Conquesting (Spiriva Handihaler)', 2000),

    ('Drugs.com', '18-028', 'Stiolto', 'D GRx m.D m.GRx Competitive Conquesting (See List)', 15374),
    ('GoodRx', '18-028', 'Stiolto', 'D GRx m.D m.GRx Competitive Conquesting (See List)', 3300),

    ('Drugs.com', '17-147', 'Trintellix', 'D GoodRx m.D Competitive Conquesting (Non-exclusive, See list)', 4996), 
    ('GoodRx', '17-147', 'Trintellix', 'D GoodRx m.D Competitive Conquesting (Non-exclusive, See list)', 2000), 
    ]

def ADD_SPECIAL_CASE(df):
    df.loc[(df['Brand'] == 'Harvoni') &
           (df['DAS Line Item Name'].str.contains('HL D LS m.HL m.D Sponsorship of Hep C Microsite')),
           'Special Case'] = 'CPM Microsite'
