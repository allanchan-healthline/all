MO_YEAR = (11, 2017)

MONTHLY_SHEET_NAME = {'pas': 'Nov', 'cpuv goals': 'Nov'}

UV_TRACKER_GSHEET = {'Drugs.com': '1gJ0HtjQ4GKVEluwK9ZkCrIoUgQ7O8k3Uy61-qW7kdTM',
                     'Livestrong': '1N2C6GyQHf9VeS-S0hadznCUeHLVDILHOHxowumOBA4o',
                     'EmpowHer': '1E6joonYUXVjcAUe9jCYwY-O7KyJJrex6Wm6vvNKbaAA',
                     'HL': '1nmQxUMXVW-q_WhqoDI8Sl-bNfGpVFJjbE0w9EN9Ui0Y',
                     'MNT': '1nmQxUMXVW-q_WhqoDI8Sl-bNfGpVFJjbE0w9EN9Ui0Y'}

MNT_UV_TRACKER_TABS = ['Humira AS MNT', 'Humira CD MNT', 'Humira PSA MNT', 'Humira PSO MNT',
                       'Humira RA MNT', 'Humira UC MNT']

LS_CORRECT_RATE_DICT = {'Duopa': 1.00,
                        'Dupixent': 1.00,
                        'Humira CD': 1.00,
                        'Synvisc Brand': 1.50, 
                        'Toujeo': 0.90,
                        'Trintellix': 1.00,
                        'Trulance': 1.00}

UV_TRACKER_RENAME_DICT = {'Drugs.com': {},

                          'Livestrong': {},

                          'EmpowHer': {},

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
    ('Drugs.com', '17-098', 'Ocrevus', 'D GoodRx m.D Competitive Conquesting (Non-exclusive on Drugs; Exclusive on GoodRx; Tecfidera, Tysabri, Gilenya, Zinbryta, & Aubagio)', 1900),
    ('GoodRx', '17-098', 'Ocrevus', 'D GoodRx m.D Competitive Conquesting (Non-exclusive on Drugs; Exclusive on GoodRx; Tecfidera, Tysabri, Gilenya, Zinbryta, & Aubagio)', 900),
    ('Drugs.com', '17-031', 'Cialis', 'D m.D Competitive Conquesting (Cialis, non-exclusive)', 26000),
    ('Drugs.com', '17-006', 'Kisqali', 'HL D GoodRx m.HL m.D Competitive Conquesting', 5757),
    ('GoodRx', '17-006', 'Kisqali', 'HL D GoodRx m.HL m.D Competitive Conquesting', 3733),
    ('Drugs.com', '17-147', 'Trintellix', 'D GoodRx m.D Competitive Conquesting (Non-exclusive, See list)', 5250),
    ('GoodRx', '17-147', 'Trintellix', 'D GoodRx m.D Competitive Conquesting (Non-exclusive, See list)', 2000), 
    ('Drugs.com', '17-102', 'Xiafle', 'D GoodRx m.D Competitive Conquesting (Xiaflex)', 640), 
    ('GoodRx', '17-102', 'Xiafle', 'D GoodRx m.D Competitive Conquesting (Xiaflex)', 100)]

def ADD_SPECIAL_CASE(df):
    df.loc[(df['Brand'] == 'Cialis') &
           (df['DAS Line Item Name'] == 'D m.D Competitive Conquesting (Cialis, non-exclusive)'),
           'Special Case'] = 'Pay Drugs up to 26k UVs & get paid up to 22k UVs (Undersold)'
    df.loc[df['Brand'] == 'Toujeo', 'Special Case'] = 'Flat-fee'
    df.loc[(df['Brand'] == 'Harvoni') &
           (df['DAS Line Item Name'].str.contains('HL D LS m.HL m.D Sponsorship of Hep C Microsite')),
           'Special Case'] = 'CPM Microsite'
