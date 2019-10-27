"""
We will request line status for all lines (preferably including buses, nat rail etc.)
from the TFL API.

We will transform this into my desired format, and append it to a file or database.

We will finally set up a script that periodically performs this action (e.g. every 15 minutes)
"""

import requests
import os.path
import csv
import datetime

credentials_file = 'apiCredentials.txt'


def read_api_credentials(txt_file):
    """User is required to save a txt file with two lines: the first being their applicationID
    and the second being their application key"""
    global credentials
    credentials = {}
    with open(txt_file) as f:
        credentials['app_id'] = f.readline().rstrip()
        credentials['app_key'] = f.readline().rstrip()


read_api_credentials(credentials_file)


def request_meta_modes():
    # Request list of valid 'modes' (meta)
    valid_modes_url = 'https://api.tfl.gov.uk/Line/Meta/Modes'
    response = requests.get(valid_modes_url, params=credentials)
    valid_modes = []
    for d in response.json():
        valid_modes.append(d['modeName'])
    return valid_modes


def request_meta_severitycodes():
    """Request lookup for 'severity codes' """
    severity_codes_url = 'https://api.tfl.gov.uk/Line/Meta/Severity'
    response = requests.get(severity_codes_url, params=credentials)
    return response.json()


def request_tube_status():
    """Request status for tube, DLR and Overground
    we could also ask for national rail, river bus and bus services, but leaving out for now"""
    tube_status_url = 'https://api.tfl.gov.uk/Line/Mode/tube,overground,dlr/Status'
    response = requests.get(tube_status_url, params=credentials)
    tube_status_json = response.json()
    return tube_status_json


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


def append_to_csv(csvfile, row_items):
    with open(csvfile, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(row_items)


def extract_status_row(timestamp, line_status):
    """Take a single linestatus from the status json and extracts data ready for a csv row"""
    return [timestamp, line_status['modeName'], line_status['id'], line_status['name']
            , '||'.join([str(status['statusSeverity']) for status in line_status['lineStatuses']])
            , '||'.join([status['statusSeverityDescription'] for status in line_status['lineStatuses']])
            ]


def main():
    csv_file = 'data/statuslog.csv'
    create_csv(csv_file, ['timestamp', 'modeName', 'lineId', 'lineName', 'statusSeverity', 'severityDesc'])
    request_time = datetime.datetime.now()
    status_json = request_tube_status()
    for line in status_json:
        row_items = extract_status_row(request_time, line)
        append_to_csv(csv_file, row_items)
