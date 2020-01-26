import csv
import os.path


def create_csv(csv_out, headers):
    if csv_out[-4:] != '.csv':
        raise ValueError('Expecting a csv_out argument ending with ".csv"')
    if os.path.isfile(csv_out):
        print(csv_out + ' already exists. File will not be overwritten')
        return
    if type(headers) is not list:
        raise ValueError('Expecting a list of headers as the headers argument')

    f = open(csv_out, 'x', newline='')  # x to create file: error if it already exists
    writer = csv.writer(f)
    writer.writerow(headers)
    f.close()


def read_api_credentials(txt_file):
    """User is required to save a txt file with two lines: the first being their applicationID
    and the second being their application key"""
    credentials = {}
    with open(txt_file) as f:
        credentials['app_id'] = f.readline().rstrip()
        credentials['app_key'] = f.readline().rstrip()
    return credentials


def append_to_csv(csvfile, row_items):
    with open(csvfile, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(row_items)
