from NEW_helpers import *
from delivery_helpers import *
from always_up2date_helpers import *
from adjuster_helpers import *
from adjuster_email_helpers import *

import os
from shutil import copy2
from shutil import move
import pickle
import pandas as pd
from datetime import datetime

HAS_CHANGED = {}

#############################################
# Super Class
#############################################

class DataFlow():
    DIR_PICKLES = None
    MONTHLY_SHEET_NAME = None
    UV_TRACKER_GSHEET = None
    LS_CORRECT_RATE_DICT = None
    DRUGS_CORRECT_RATE_LIST = None
    TEMP_FIX_DAS4FLAT_FEE = None

    def __init__(self):
        pass

    def pickle_exists(self):
        return os.path.exists(DataFlow.DIR_PICKLES + '/' + self.pickle_name)

    def load_pickle(self):
        with open(DataFlow.DIR_PICKLES + '/' + self.pickle_name, 'rb') as f:
            return pickle.load(f)

    def save_pickle(self, df):
        with open(DataFlow.DIR_PICKLES + '/' + self.pickle_name, 'wb') as f:
            pickle.dump(df, f)

    def update_has_changed_dict(self):
        # Whether this file is changing or not
        if len(self.dependency_list) == 0:
            # No other file to depend on
            HAS_CHANGED[self.name] = self.this_has_changed()
        else:
            # Check all files to depend on
            self.dependency_check()
            HAS_CHANGED[self.name] = False
            for obj in self.dependency_list:
                if HAS_CHANGED[obj.name]:
                    HAS_CHANGED[self.name] = True

        # Create a df
        if self.use_pickle and self.pickle_exists() and not HAS_CHANGED[self.name]:
            return
        df = self.perform_op()
        self.save_pickle(df)
        return

    def dependency_check(self):
        for obj in self.dependency_list:
            if obj.name in HAS_CHANGED:
                continue
            obj.update_has_changed_dict()

    def check_pickle_exists(self):
        return os.path.exists(DataFlow.DIR_PICKLES + '/' + self.check_pickle_name)

    def get_check_pickle(self):
        with open(DataFlow.DIR_PICKLES + '/' + self.check_pickle_name, 'rb') as f:
            return pickle.load(f)

    def save_check_pickle(self, df):
        with open(DataFlow.DIR_PICKLES + '/' + self.check_pickle_name, 'wb') as f:
            pickle.dump(df, f)

#############################################
# CPUV
#############################################

class MicrositeUVs(DataFlow):
    def __init__(self, site, mo_year):
        self.use_pickle = True
        self.site = site
        self.mo_year = mo_year
        self.pickle_name = 'microsite_uvs_' + site + '.pickle'
        self.name = 'microsite_uvs_' + site
        self.dependency_list = []

    def get_raw_df(self):
        try:
            raw_df = get_microsite_uvs(self.site, self.mo_year, DataFlow.UV_TRACKER_GSHEET[self.site], DataFlow.MONTHLY_SHEET_NAME['cpuv goals'])
        except Exception as e:
            print('data error: calling get_raw_df with exception: {}'.format(e))
        else:
            return raw_df

    def get_labeled_df(self):
        try:
            labeled_df = label_microsite_uvs(self.get_raw_df(), self.mo_year, DataFlow.MONTHLY_SHEET_NAME['cpuv goals'])
        except Exception as e:
            print('data error: calling get_labeled_df with exception: {}'.format(e))
        else:
            return labeled_df

    def perform_op(self):
        return self.get_labeled_df()

    def this_has_changed(self):
        pickled = get_last_modified_local(DataFlow.DIR_PICKLES + '/' + self.pickle_name)
        if pickled is None:
            return True

        tracker_last_modified = get_last_modified_gdrive(DataFlow.UV_TRACKER_GSHEET[self.site])
        goals_last_modified = get_last_modified_gdrive(CPUV_GOALS_WHICH_GSHEET[self.mo_year[1]])

        if (pickled < tracker_last_modified) or (pickled < goals_last_modified):  # add 1 min extra
            return True

        return False

class CC_UVs(DataFlow):
    def __init__(self, site, mo_year):
        self.use_pickle = True
        self.site = site
        self.mo_year = mo_year
        self.pickle_name = 'cc_uvs_' + site + '.pickle'
        self.name = 'cc_uvs_' + site
        self.dependency_list = []

    def get_raw_df(self):
        try:
            raw_df = get_cc_uvs(self.site, self.mo_year, DataFlow.MONTHLY_SHEET_NAME['cpuv goals'])
        except Exception as e:
            print('data error: calling get_raw_df with exception {}'.format(e))
        else:
            return raw_df

    def get_labeled_df(self):
        try:
            labeled_df = label_cc_uvs(self.get_raw_df(), self.mo_year, DataFlow.MONTHLY_SHEET_NAME['cpuv goals'])
        except Exception as e:
            print('data error: calling get_labeled_df with exception {}'.format(e))
        else:
            return labeled_df

    def perform_op(self):
        return self.get_labeled_df()

    def this_has_changed(self):
        pickled = get_last_modified_local(DataFlow.DIR_PICKLES + '/' + self.pickle_name)
        if pickled is None:
            return True

        tracker_last_modified = get_last_modified_gdrive(CC_TRACKER_GSHEET[self.site])
        goals_last_modified = get_last_modified_gdrive(CPUV_GOALS_WHICH_GSHEET[self.mo_year[1]])

        if (pickled < tracker_last_modified) or (pickled < goals_last_modified):  # add 1 min extra
            return True

        return False

class CPUV_Goals(DataFlow):
    def __init__(self, mo_year):
        self.use_pickle = True
        self.mo_year = mo_year
        self.pickle_name = 'cpuv_goals.pickle'
        self.name = 'cpuv_goals'
        self.dependency_list = []

    def perform_op(self):
        return get_cpuv_goals(self.mo_year[1], DataFlow.MONTHLY_SHEET_NAME['cpuv goals'])

    def this_has_changed(self):
        pickled = get_last_modified_local(DataFlow.DIR_PICKLES + '/' + self.pickle_name)
        last_modified = get_last_modified_gdrive(CPUV_GOALS_WHICH_GSHEET[self.mo_year[1]])
        if pickled is None:
            return True
        elif pickled < last_modified:  # add 1 min extra
            return True
        return False

class CPUV(DataFlow):
    def __init__(self, mo_year):
        self.use_pickle = True
        self.mo_year = mo_year
        self.pickle_name = 'cpuv.pickle'
        self.name = 'cpuv'
        self.dependency_list = [CPUV_Goals(self.mo_year)]
        for site in ['Drugs.com', 'Livestrong', 'EmpowHer', 'HL', 'MNT', 'BCO']:
            if site not in DataFlow.UV_TRACKER_GSHEET:
                continue
            self.dependency_list.append(MicrositeUVs(site, self.mo_year))
        for site in ['Drugs.com', 'GoodRx']:
            self.dependency_list.append(CC_UVs(site, self.mo_year))

    def perform_op(self):
        df_list = []
        for dependency in self.dependency_list:
            if dependency.name != 'cpuv_goals':
                df = dependency.load_pickle()
                df_list.append(df)
        return pd.concat(df_list)

#############################################
# CPM
#############################################

class DFP_MTD_AllRaw(DataFlow):
    def __init__(self, last_delivery_date, path_csv, emailed_csv):
        self.use_pickle = True
        self.last_delivery_date = last_delivery_date
        self.path_csv = path_csv  # None if API
        self.emailed_csv = emailed_csv
        self.pickle_name = 'dfp_mtd_all_raw.pickle'
        self.check_pickle_name = 'dfp_check_' + str(self.last_delivery_date) + '.pickle'
        self.last_csv_name = 'last_pre_pulled_dfp_mtd_all_raw.csv'
        self.name = 'dfp_mtd_all_raw'
        self.dependency_list = []

    def perform_op(self):
        return get_dfp_mtd_all(self.last_delivery_date, self.path_csv, self.emailed_csv)

    def is_same_csv(self):
        path_last_csv = DataFlow.DIR_PICKLES + '/' + self.last_csv_name
        if os.path.exists(path_last_csv):
            timestamp_last = get_last_modified_local(path_last_csv)
            timestamp_this = get_last_modified_local(self.path_csv)
            if timestamp_last == timestamp_this:
                return True
        return False

    def this_has_changed(self):
        # If using csv, compare last modified datetime of csv with last used csv
        # Don't load/save check data
        if self.path_csv is not None:
            if self.is_same_csv():
                return False
            copy2(self.path_csv, DataFlow.DIR_PICKLES + '/' + self.last_csv_name)
            return True

        # If there's no check data, save current check data
        current = get_dfp_check(self.last_delivery_date)
        if self.check_pickle_exists():
            existing = self.get_check_pickle()
            if current.equals(existing):
                return False

        self.save_check_pickle(current)
        return True

class ExcludeList(DataFlow):
    def __init__(self):
        self.use_pickle = True
        self.pickle_name = 'exclude_list.pickle'
        self.name = 'exclude_list'
        self.dependency_list = []

    def perform_op(self):
        return get_exclude_list()

    def this_has_changed(self):
        pickled = get_last_modified_local(DataFlow.DIR_PICKLES + '/' + self.pickle_name)
        last_modified = get_last_modified_gdrive('10RD_2cF0jytoCBT-2bui1pRBiP9B4UPdB0VWzxsGeg4')
        if pickled is None:
            return True
        elif pickled < last_modified:  # add 1 min extra
            return True
        return False

class DFP_MTD_All(DataFlow):
    def __init__(self, last_delivery_date, path_csv, emailed_csv):
        self.use_pickle = True
        self.last_delivery_date = last_delivery_date
        self.path_csv = path_csv  # None if API
        self.emailed_csv = emailed_csv
        self.pickle_name = 'dfp_mtd_all.pickle'
        self.name = 'dfp_mtd_all'
        self.dependency_list = [DFP_MTD_AllRaw(self.last_delivery_date, self.path_csv, self.emailed_csv),
                                ExcludeList()]

    def perform_op(self):
        df = DFP_MTD_AllRaw(self.last_delivery_date, self.path_csv, self.emailed_csv).load_pickle() 
        return label_dfp_mtd_all(df)

class TradeDeskRaw(DataFlow):
    def __init__(self, mo_year):
        self.use_pickle = True
        self.mo_year = mo_year
        self.pickle_name = 'ttd_raw.pickle'
        self.name = 'ttd_raw'
        self.dependency_list = [AdjusterTTD_Path(self.mo_year)]

    def perform_op(self):
        adjuster_ttd_path = AdjusterTTD_Path(self.mo_year).load_pickle()
        return get_tradedesk_report(adjuster_ttd_path)

class TradeDesk(DataFlow):
    def __init__(self, mo_year):
        self.use_pickle = True
        self.mo_year = mo_year
        self.pickle_name = 'ttd.pickle'
        self.name = 'ttd'
        self.dependency_list = [TradeDeskRaw(self.mo_year),
                                DAS(self.mo_year)]

    def perform_op(self):
        df = TradeDeskRaw(self.mo_year).load_pickle()
        return label_tradedesk_report(df)

class CPM(DataFlow):
    def __init__(self, last_delivery_date, path_csv, emailed_csv):
        self.use_pickle = True
        self.last_delivery_date = last_delivery_date
        self.path_csv = path_csv
        self.emailed_csv = emailed_csv
        self.mo_year = (last_delivery_date.month, last_delivery_date.year)
        self.pickle_name = 'cpm.pickle'
        self.name = 'cpm'
        self.dependency_list = [DFP_MTD_All(self.last_delivery_date, self.path_csv, self.emailed_csv),
                                TradeDesk(self.mo_year)]

    def perform_op(self):
        df_dfp = DFP_MTD_All(self.last_delivery_date, self.path_csv, self.emailed_csv).load_pickle()
        df_ttd = TradeDesk(self.mo_year).load_pickle()
        return pd.concat([df_dfp, df_ttd])

#############################################
# All1 = (CPM + CPUV) x Salesforce (a.k.a. DAS)
#############################################

class DAS(DataFlow):
    def __init__(self, mo_year):
        self.use_pickle = True
        self.mo, self.year = mo_year
        self.pickle_name = 'das.pickle'
        self.check_pickle_name = 'check_das.pickle'
        self.name = 'das'
        self.dependency_list = []

    def perform_op(self):
        return make_das(use_scheduled_units=False, export=False)

    def this_has_changed(self):
        # If there's no check data, save current check data
        das = make_das(use_scheduled_units=False, export=False)
        current = das[das[str(self.mo) + '/' + str(self.year)] > 0]
        if self.check_pickle_exists():
            existing = self.get_check_pickle()
            if current.equals(existing):
                return False

        self.save_check_pickle(current)
        return True

class All1(DataFlow):
    def __init__(self, last_delivery_date, path_csv, emailed_csv):
        self.use_pickle = True
        self.last_delivery_date = last_delivery_date
        self.path_csv = path_csv
        self.emailed_csv = emailed_csv
        self.mo_year = (last_delivery_date.month, last_delivery_date.year)
        self.pickle_name = 'all1.pickle'
        self.name = 'all1'
        self.dependency_list = [CPM(self.last_delivery_date, self.path_csv, self.emailed_csv),
                                CPUV(self.mo_year),
                                DAS(self.mo_year)]

    def perform_op(self):
        df_cpm = CPM(self.last_delivery_date, self.path_csv, self.emailed_csv).load_pickle()
        df_cpuv = CPUV(self.mo_year).load_pickle()
        return make_all1(df_cpm, df_cpuv, DataFlow.TEMP_FIX_DAS4FLAT_FEE)

#############################################
# Site Goals = Salesforce + PAS + CPUV Goals Sheet
#############################################

class PAS(DataFlow):
    def __init__(self, mo_year):
        self.use_pickle = True
        self.mo_year = mo_year
        self.pickle_name = 'pas.pickle'
        self.name = 'pas'
        self.dependency_list = []

    def perform_op(self):
        return get_pas(self.mo_year[1], DataFlow.MONTHLY_SHEET_NAME['pas'])

    def this_has_changed(self):
        pickled = get_last_modified_local(DataFlow.DIR_PICKLES + '/' + self.pickle_name)
        last_modified = get_last_modified_gdrive(PAS_WHICH_GSHEET[self.mo_year[1]])
        if pickled is None:
            return True
        elif pickled < last_modified:  # add 1 min extra
            return True
        return False

class SiteGoals(DataFlow):
    def __init__(self, mo_year):
        self.use_pickle = True
        self.mo_year = mo_year
        self.pickle_name = 'site_goals.pickle'
        self.name = 'site_goals'
        self.dependency_list = [DAS(self.mo_year), PAS(self.mo_year), CPUV_Goals(self.mo_year)]

    def perform_op(self):
        return get_site_goals(self.mo_year, DataFlow.MONTHLY_SHEET_NAME['pas'],
                              DataFlow.MONTHLY_SHEET_NAME['cpuv goals'],
                              DataFlow.LS_CORRECT_RATE_DICT,
                              DataFlow.DRUGS_CORRECT_RATE_LIST,
                              DataFlow.TEMP_FIX_DAS4FLAT_FEE)

#############################################
# Adjuster file path
#############################################

class AdjusterDFP_Path(DataFlow):
    def __init__(self, mo_year):
        self.use_pickle = True
        self.mo_year = mo_year
        self.pickle_name = 'adjuster_dfp_path.pickle'
        self.check_pickle_name = 'adjuster_dfp_datetime.pickle'
        self.name = 'adjuster_dfp_path'
        self.dependency_list = []

    def perform_op(self):
        if self.check_pickle_exists():
            sent_since_local_datetime = self.get_check_pickle()
        else:
            sent_since_local_datetime = datetime(self.mo_year[1], self.mo_year[0], 1)

        csv_filename, sent_local_datetime = get_newest_csv_filename_n_sent_local_datetime(sent_since_local_datetime, 'Your report: CDR Month To Date', self.mo_year)

        # Move csv from local directory to pickle directory
        path2csv_filename = DataFlow.DIR_PICKLES + '/' + csv_filename
        move(csv_filename, path2csv_filename)

        self.save_check_pickle(sent_local_datetime)
        return path2csv_filename

    def this_has_changed(self):
        if self.check_pickle_exists():
            adjuster_dfp_datetime = self.get_check_pickle()
            if not exists_new_report(adjuster_dfp_datetime, 'Your report: CDR Month To Date', self.mo_year):
                return False

        return True

class AdjusterTTD_Path(DataFlow):
    def __init__(self, mo_year):
        self.use_pickle = True
        self.mo_year = mo_year
        self.pickle_name = 'adjuster_ttd_path.pickle'
        self.check_pickle_name = 'adjuster_ttd_datetime.pickle'
        self.name = 'adjuster_ttd_path'
        self.dependency_list = []

    def perform_op(self):
        if self.check_pickle_exists():
            sent_since_local_datetime = self.get_check_pickle()
        else:
            sent_since_local_datetime = datetime(self.mo_year[1], self.mo_year[0], 1)
        csv_filename, sent_local_datetime = get_newest_csv_filename_n_sent_local_datetime(sent_since_local_datetime, 'Your report: Trade Desk Local Data', self.mo_year)

        # Move csv from local directory to pickle directory
        path2csv_filename = DataFlow.DIR_PICKLES + '/' + csv_filename
        move(csv_filename, path2csv_filename)

        self.save_check_pickle(sent_local_datetime)
        return path2csv_filename

    def this_has_changed(self):
        if self.check_pickle_exists():
            adjuster_dfp_datetime = self.get_check_pickle()
            if not exists_new_report(adjuster_dfp_datetime, 'Your report: Trade Desk Local Data', self.mo_year):
                return False

        return True

#############################################
# 3rd Party Imps
#############################################

class ThirdPartyDFP(DataFlow):
    def __init__(self, mo_year, last_delivery_date):
        self.use_pickle = True
        self.mo_year = mo_year
        self.last_delivery_date = last_delivery_date
        self.pickle_name = 'third_party_dfp.pickle'
        self.name = 'third_party_dfp'
        self.dependency_list = [AdjusterDFP_Path(self.mo_year),
                                DFP_MTD_AllRaw(self.last_delivery_date, None, None)]

    def perform_op(self):
        adjuster_dfp_path = AdjusterDFP_Path(self.mo_year).load_pickle()
        df = get_grouped_aj3rd(adjuster_dfp_path, for_1st_party='DFP')
        df = get_labeled_grouped_aj3rd_for_dfp(df)
        return df

class ThirdPartyTTD(DataFlow):
    def __init__(self, mo_year):
        self.use_pickle = True
        self.mo_year = mo_year
        self.pickle_name = 'third_party_ttd.pickle'
        self.name = 'third_party_ttd'
        self.dependency_list = [AdjusterTTD_Path(self.mo_year),
                                DAS(self.mo_year)]

    def perform_op(self):
        adjuster_ttd_path = AdjusterTTD_Path(self.mo_year).load_pickle()
        df = get_grouped_aj3rd(adjuster_ttd_path, for_1st_party='TTD')
        df = get_labeled_grouped_aj3rd_for_ttd(df)
        return df

class ThirdPartyImps(DataFlow):
    def __init__(self, mo_year, last_delivery_date):
        self.use_pickle = True
        self.mo_year = mo_year
        self.last_delivery_date = last_delivery_date
        self.pickle_name = 'third_party_imps.pickle'
        self.name = 'third_party_imps'
        self.dependency_list = [DAS(self.mo_year),
                                ThirdPartyDFP(self.mo_year, self.last_delivery_date),
                                ThirdPartyTTD(self.mo_year)]

    def perform_op(self):
        df_dfp = ThirdPartyDFP(self.mo_year, self.last_delivery_date).load_pickle()
        df_ttd = ThirdPartyTTD(self.mo_year).load_pickle()
        df = pd.concat([df_dfp, df_ttd])
        df = get_formatted_aj3rd(df)
        df = get_billable_aj3rd(df)
        return df

#############################################
# All of above
#############################################

class RunThisTo(DataFlow):
    def __init__(self, last_delivery_date, path_csv, emailed_csv):
        self.use_pickle = True
        self.last_delivery_date = last_delivery_date
        self.path_csv = path_csv
        self.emailed_csv = emailed_csv
        self.mo_year = (last_delivery_date.month, last_delivery_date.year)
        self.pickle_name = 'yum.pickle'
        self.name = 'something'
        self.dependency_list = [All1(self.last_delivery_date, self.path_csv, self.emailed_csv),
                                SiteGoals(self.mo_year),
                                ThirdPartyImps(self.mo_year, self.last_delivery_date)]

    def perform_op(self):
        return '^_^'
