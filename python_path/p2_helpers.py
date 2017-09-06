import pandas as pd
import numpy as np

pd.options.mode.chained_assignment = None

def add_allergan_revenue2delivery(mtd_delivery, das, das_month):
    mtd_delivery['Billable Imps'] = [int(bi) for bi in mtd_delivery['Billable Imps']]
    mtd_delivery.loc[mtd_delivery['Site'] == 'Drugs', 'Site'] = 'D'
    mtd_delivery = mtd_delivery.rename(columns={'Advertiser': 'Brand', 'Billable Imps': 'Delivered Imps (Allergan Moat)'})

    selected_das = das[(das['Account Name'] == 'Allergan') &
                       (das['Price Calculation Type'] == 'CPM') &
                       (das[das_month] > 0) &
                       (das['Sales Price'] > 0)]
    selected_das['Site'] = [ld.split()[0] for ld in selected_das['Line Description']]

    df = pd.merge(mtd_delivery, selected_das, how='left', on=['Brand', 'Site']).rename(columns={'Sales Price': 'CPM', das_month: 'Goal'})
    df['MTD Billable Imps'] = df['Delivered Imps (Allergan Moat)']
    df.loc[df['Delivered Imps (Allergan Moat)'] > df['Goal'], 'MTD Billable Imps'] = \
        df.loc[df['Delivered Imps (Allergan Moat)'] > df['Goal'], 'Goal']
    df['MTD Revenue'] = df['MTD Billable Imps'] / 1000.0 * df['CPM']

    #3. Clean up
    df = df[pd.notnull(df['Campaign Name'])]
    df = df[['Campaign Name', 'Line Description', 'CPM', 'MTD Revenue', 'MTD Billable Imps', 'Goal', 'Delivered Imps (Allergan Moat)']]
    df = df.sort_values(['Campaign Name', 'Line Description'])

    return df

def prep_dcm_sf_linking(dcm_plmnt_ids):
    dcm_plmnt_ids['DAS Line Item Name'] = [(lin.strip() if isinstance(lin, str) else lin) for lin in dcm_plmnt_ids['DAS Line Item Name']]

    #Extract BBR # from Order. If no 'BBR' is found, enter zero
    def pickup_bbr(order):
        if 'BBR' in order.upper():
            return order[-6:]
        else:
            return 0

    dcm_plmnt_ids['(Order)BBR #'] = [pickup_bbr(order) for order in dcm_plmnt_ids['Order']]

    #Identify DAS CPM rows
    dcm_plmnt_ids['Imp Type'] = ['Imp(Other)' if bbr == 0 else 'CPM' for bbr in dcm_plmnt_ids['(Order)BBR #']]

    ##MNT orders
    dcm_plmnt_ids.loc[[('MNT' in o) for o in dcm_plmnt_ids['Order']], 'Imp Type'] = 'Imp(MNT)'

    ##CPUV imps
    dcm_plmnt_ids.loc[dcm_plmnt_ids['Line item'].str.contains('CPUV', case=False), 'Imp Type'] = 'Imp(CPUV)'
    dcm_plmnt_ids.loc[dcm_plmnt_ids['Line item'].str.contains('_CC_', case=False), 'Imp Type'] = 'Imp(CPUV)'
    dcm_plmnt_ids.loc[dcm_plmnt_ids['Line item'].str.contains('ibrance', case=False), 'Imp Type'] = 'CPM'
    dcm_plmnt_ids.loc[dcm_plmnt_ids['Line item'].str.contains('synvisc', case=False), 'Imp Type'] = 'Imp(CPUV)'

    ##Test imps
    dcm_plmnt_ids.loc[dcm_plmnt_ids['Line item'].str.contains('test', case=False) & np.invert(dcm_plmnt_ids['Line item'].str.contains('contest', case=False)),
             'Imp Type'] = 'Imp(Test)'

    ##Defaults imps
    dcm_plmnt_ids.loc[dcm_plmnt_ids['Order'].str.contains('defaults', case=False), 'Imp Type'] = 'Imp(Defaults)'

    #Clean up
    dcm_plmnt_ids = dcm_plmnt_ids[dcm_plmnt_ids['Imp Type'] == 'CPM'][['3rd Party Creative ID', '(Order)BBR #', 'DAS Line Item Name']].drop_duplicates()
    dcm_plmnt_ids = dcm_plmnt_ids.rename(columns={'3rd Party Creative ID': 'Placement ID',
                                                  '(Order)BBR #': 'BBR', 'DAS Line Item Name': 'Line Description'})

    return dcm_plmnt_ids

def select_camps(all_data):
    """
    CTCA 4427
    Dexcom 7384, exclude Custom Program, exclude non-Dexcom
    Latuda 4864
    MSK 7252
    Pfizer 3148
    Spark 3382, exclude PsO Video
    Vyvanse 5667
    """
    selected = all_data[[aid in [4427, 7384, 4864, 7252, 3148, 3382, 5667] for aid in all_data['Account ID']]]
    selected = selected[np.invert((selected['Account ID'] == 7384) & (selected['Placement'].str.contains('Custom Program')))]
    selected = selected[np.invert((selected['Account ID'] == 7384) & np.invert(selected['Campaign'].str.contains('Dexcom')))]
    selected = selected[np.invert((selected['Account ID'] == 3382) & (selected['Placement'].str.contains('_PsVideoIntegration_')))]

    return selected

def add_sem_labeling(dcm):
    """
    Humira RA
    """
    dcm.loc[(dcm['Campaign'] == 'ABV_2017_HRA_BRD_DISPLAY') &
            (dcm['Placement'].str.contains('_HealthlineAudienceRetargeting_')),
            ('BBR', 'Line Description')] = ('17-028', 'WWW m.WWW Rheumatoid Arthritis Retargeting')
    return dcm

def dcm_sf_linking(dcm, prep, das, das_month):
    #1. Add BBR, Campaign Name, and Line Description from DAS to DCM report
    for df in [dcm, prep]:
        df['Placement ID'] = [str(pid).strip() for pid in df['Placement ID']]

    combined_dcm = pd.merge(dcm, prep.drop_duplicates('Placement ID', keep=False), how='left', on='Placement ID')
    combined_dcm = add_sem_labeling(combined_dcm)

    das_cpm_thismonth = das[(das[das_month] > 0) &
                            (das['Price Calculation Type'] == 'CPM')]

    das_cpm_thismonth_1 = das_cpm_thismonth[['BBR', 'Campaign Name', 'Line Description']]
    combined_dcm = pd.merge(combined_dcm, das_cpm_thismonth_1.drop_duplicates(['BBR', 'Line Description'], keep=False),
                            how='left', on=['BBR', 'Line Description'])

    #2. Group by HL Campaign and Placement, and add MTD billable imps and revenue
    grouped = combined_dcm[['Campaign Name', 'Line Description', 'Impressions']]\
        .groupby(['Campaign Name', 'Line Description']).sum().reset_index()

    das_cpm_thismonth_2 = das_cpm_thismonth[['Campaign Name', 'Line Description', 'Flight Type', 'Sales Price', das_month]]\
        .rename(columns={das_month: 'Goal'})
    grouped = pd.merge(grouped, das_cpm_thismonth_2.drop_duplicates(['Campaign Name', 'Line Description'], keep=False),
                       how='left', on=['Campaign Name', 'Line Description'])

    grouped['MTD Billable Imps'] = grouped['Impressions']
    grouped.loc[(grouped['Flight Type'] == 'Monthly') & (grouped['Impressions'] > grouped['Goal']), 'MTD Billable Imps'] = \
        grouped.loc[(grouped['Flight Type'] == 'Monthly') & (grouped['Impressions'] > grouped['Goal']), 'Goal']
    grouped['MTD Revenue'] = grouped['MTD Billable Imps'] / 1000 * grouped['Sales Price']

    #3. Reorder columns and change names
    grouped = grouped[['Campaign Name', 'Line Description', 'Flight Type', 'Sales Price', 'MTD Revenue', 'MTD Billable Imps', 'Goal', 'Impressions']]
    grouped = grouped.rename(columns={'Sales Price': 'CPM', 'Impressions': 'Delivered Imps (DCM)'})
    grouped = grouped.sort_values(['Campaign Name', 'Line Description'])

    return grouped

def camp_rev(df):
    return df[['Campaign Name', 'MTD Revenue']].groupby('Campaign Name').sum().reset_index()




