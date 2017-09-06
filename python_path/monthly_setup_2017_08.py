
MO_YEAR = (8, 2017)

MONTHLY_SHEET_NAME = {'pas': 'Aug', 'cpuv goals': 'Aug'}

UV_TRACKER_PATH = {'Drugs.com': '/home/kumiko/always_up2date/uv_trackers/Drugs com_Microsite_UV_Tracker - August 2017 V2.xlsx',
                   'Livestrong': '/home/kumiko/always_up2date/uv_trackers/Livestrong_Microsite_UV_Tracker -August 2017 V2.xlsx',
                   'EmpowHer': '/home/kumiko/always_up2date/uv_trackers/EmpowHER Microsite_UV_Tracker - August 2017.xlsx',
                   'HL': '/home/kumiko/always_up2date/uv_trackers/August 2017 CPUV.xlsx',
                   'MNT': '/home/kumiko/always_up2date/uv_trackers/August 2017 CPUV.xlsx'}

MNT_UV_TRACKER_TABS = ['Humira AS MNT', 'Humira CD MNT', 'Humira PSA MNT', 'Humira PSO MNT',
                       'Humira RA MNT', 'Humira UC MNT']

LS_CORRECT_RATE_DICT = {'Duopa': 1.00,
                        'Dupixent': 1.00,
                        'Humira CD': 1.00,
                        'Synvisc Brand': 1.50, 
                        'Toujeo': 0.90,
                        'Trintellix': 1.00,
                        'Trulance': 1.00,
                        'Xiidra': 1.00}

UV_TRACKER_RENAME_DICT = {'Drugs.com': {'Aubagio- switcher': 'Aubagio Switcher',
                                        'Cosentyx AS': 'Cosentyx',
                                        'Esbiret (unbranded)': 'Esbriet unbranded',
                                        'Ocrevus (Branded)': 'Ocrevus',
                                        'Synvisc - (Brand)': 'Synvisc Brand',
                                        'Tecfidera-reimagine': 'Tecfidera-Reimagine'},

                          'Livestrong': {'Esbriet-branded': 'Esbriet branded',
                                         'Tecfidera- Brand': 'Tecfidera-Brand'},

                          'EmpowHer': {'Humira PSA': 'Humira PsA',
                                       'Humira Pso': 'Humira PsO'},

                          'Medical News Today': {'Humira AS MNT': 'Humira AS',
                                                 'Humira CD MNT': 'Humira CD',
                                                 'Humira PSA MNT': 'Humira PsA',
                                                 'Humira PSO MNT': 'Humira PsO',
                                                 'Humira RA MNT': 'Humira R.A.',
                                                 'Humira UC MNT': 'Humira UC'}}

def TEMP_FIX_DAS4FLAT_FEE(das):
    das = das.copy()
    das.loc[das['Brand'] == 'Toujeo', ('Price Calculation Type', 'Base Rate')] = ('CPUV', 0.0)
    return das

PARTNER_CAPPING_SP_CASE = [
    ('Drugs.com', '17-031', 'Cialis', 'D m.D Competitive Conquesting (Cialis, non-exclusive)', 26000),
    ('Drugs.com', '17-098', 'Ocrevus', 'D GoodRx m.D Competitive Conquesting (Non-exclusive on Drugs; Exclusive on GoodRx; Tecfidera, Tysabri, Gilenya, Zinbryta, & Aubagio)', 2507),
    ('GoodRx', '17-098', 'Ocrevus', 'D GoodRx m.D Competitive Conquesting (Non-exclusive on Drugs; Exclusive on GoodRx; Tecfidera, Tysabri, Gilenya, Zinbryta, & Aubagio)', 900),
    ('Drugs.com', '17-006', 'Kisqali', 'HL D GoodRx m.HL m.D Competitive Conquesting', 6075),
    ('GoodRx', '17-006', 'Kisqali', 'HL D GoodRx m.HL m.D Competitive Conquesting', 3733),
    ('Drugs.com', '17-147', 'Trintellix', 'D GoodRx m.D Competitive Conquesting (Non-exclusive, See list)', 5250),
    ('GoodRx', '17-147', 'Trintellix', 'D GoodRx m.D Competitive Conquesting (Non-exclusive, See list)', 2000), 
    ('Drugs.com', '17-102', 'Xiafle', 'D GoodRx m.D Competitive Conquesting (Xiaflex)', 665), 
    ('GoodRx', '17-102', 'Xiafle', 'D GoodRx m.D Competitive Conquesting (Xiaflex)', 100)]

def ADD_SPECIAL_CASE(df):
    df.loc[(df['Brand'] == 'Cialis') &
           (df['DAS Line Item Name'] == 'D m.D Competitive Conquesting (Cialis, non-exclusive)'),
           'Special Case'] = 'Pay Drugs up to 26k UVs & get paid up to 22k UVs (Undersold)'
    df.loc[df['Brand'] == 'Toujeo', 'Special Case'] = 'Flat-fee'
    df.loc[(df['Brand'] == 'Harvoni') &
           (df['DAS Line Item Name'].str.contains('HL D LS m.HL m.D Sponsorship of Hep C Microsite')),
           'Special Case'] = 'CPM Microsite'
