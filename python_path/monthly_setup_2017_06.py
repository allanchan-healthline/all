##
MO_YEAR = (6, 2017)

MONTHLY_SHEET_NAME = {'pas': 'Jun', 'cpuv goals': 'Jun'}

UV_TRACKER_PATH = {'Drugs.com': 'uv_trackers/Drugs com_Microsite_UV_Tracker - June 2017 V2.xlsx',
                   'Livestrong': 'uv_trackers/Livestrong_Microsite_UV_Tracker -June 2017 V2.xlsx',
                   'EmpowHer': 'uv_trackers/EmpowHER Microsite_UV_Tracker - June 2017.xlsx',
                   'HL': 'uv_trackers/June 2017 CPUV.xlsx',
                   'MNT': 'uv_trackers/June 2017 CPUV.xlsx'}

MNT_UV_TRACKER_TABS = ['Humira AS MNT', 'Humira CD MNT', 'Humira PSA MNT', 'Humira PSO MNT',
                       'Humira RA MNT', 'Humira UC MNT', 'Synthroid MNT']

LS_CORRECT_RATE_DICT = {'Bydureon': 0.80,
                        'Duopa': 1.00,
                        'Dupixent': 1.00,
                        'Humira CD': 1.00,
                        'Toujeo': 0.90,
                        'Trintellix': 1.00,
                        'Trulance': 1.00,
                        'Xiidra': 1.00}

UV_TRACKER_RENAME_DICT = {'Drugs.com': {'Aubagio- naive': 'Aubagio Naive',
                                        'Aubagio- switcher': 'Aubagio Switcher',
                                        'Cosentyx AS': 'Cosentyx',
                                        'Esbriet (branded)': 'Esbriet branded',
                                        'Esbiret (unbranded)': 'Esbriet unbranded',
                                        'Ocrevus Unbranded': 'Ocrevus',
                                        'Sandosatin': 'Sandostatin',
                                        'Synvisc - (Brand)': 'Synvisc Brand',
                                        'Tecfidera-reimagine': 'Tecfidera-Reimagine',
                                        'Toujeo BP': 'Toujeo'},

                          'Livestrong': {'Esbriet-branded': 'Esbriet branded',
                                         'Synthroid.': 'Synthroid',
                                         'Tasinga': 'Tasigna',
                                         'Tecfidera- Brand': 'Tecfidera-Brand'},

                          'EmpowHer': {'Humira PSA': 'Humira PsA',
                                       'Humira Pso': 'Humira PsO'},

                          'Medical News Today': {'Humira AS MNT': 'Humira AS',
                                                 'Humira CD MNT': 'Humira CD',
                                                 'Humira PSA MNT': 'Humira PsA',
                                                 'Humira PSO MNT': 'Humira PsO',
                                                 'Humira RA MNT': 'Humira R.A.',
                                                 'Humira UC MNT': 'Humira UC',
                                                 'Synthroid MNT': 'Synthroid'}}

def TEMP_FIX_DAS4FLAT_FEE(das):
    das = das.copy()
    das.loc[das['Brand'] == 'Toujeo', ('Price Calculation Type', 'Base Rate')] = ('CPUV', 0.0)
    return das

PARTNER_CAPPING_SP_CASE = [
    ('Drugs.com', '17-031', 'Cialis', 'D m.D Competitive Conquesting (Cialis, non-exclusive)', 26000),
    ('Drugs.com', '17-147', 'Trintellix', 'D GoodRx m.D Competitive Conquesting (Non-exclusive, See list)', 5250),
    ('GoodRx', '17-147', 'Trintellix', 'D GoodRx m.D Competitive Conquesting (Non-exclusive, See list)', 2000)]

def ADD_SPECIAL_CASE(df):
    df.loc[(df['Brand'] == 'Cialis') &
           (df['DAS Line Item Name'] == 'D m.D Competitive Conquesting (Cialis, non-exclusive)'),
           'Special Case'] = 'Pay Drugs up to 26k UVs & get paid up to 22k UVs (Undersold)'
    df.loc[df['Brand'] == 'Toujeo', 'Special Case'] = 'Flat-fee'
    df.loc[(df['Brand'] == 'Harvoni') &
           (df['DAS Line Item Name'].str.contains('HL D LS m.HL m.D Sponsorship of Hep C Microsite')),
           'Special Case'] = 'CPM Microsite'
