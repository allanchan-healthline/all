from billing_helpers import *
import sys

def main(year, mo):
    csv_file_name = make_bg_as_csv(year, mo)
    gsheet_file_id = upload_bg2gdrive(year, mo, csv_file_name)
    format_bg(gsheet_file_id)
    add_cpuv_me2bg_gsheet(year, mo, gsheet_file_id)
    update_bg_cpuv_formulas(gsheet_file_id)

if __name__ == '__main__':
    year = int(sys.argv[1])
    mo = int(sys.argv[2])
    main(year, mo)
