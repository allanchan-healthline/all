from billing_helpers import *
import sys

def main(year, mo):
    excel_file_name = make_ask_tp_as_excel(year, mo)
    gsheet_file_id = upload_ask_tp2gdrive(year, mo, excel_file_name)
    format_ask_tp(gsheet_file_id)

if __name__ == '__main__':
    year = int(sys.argv[1])
    mo = int(sys.argv[2])
    main(year, mo)
