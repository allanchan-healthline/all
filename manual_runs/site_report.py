from billing_helpers import *

import sys

def main(year, mo, prefix4output):
    make_site_report_as_excel(year, mo, prefix4output)

if __name__ == '__main__':
    year = int(sys.argv[1])
    mo = int(sys.argv[2])
    prefix4output = sys.argv[3]
    main(year, mo, prefix4output)

