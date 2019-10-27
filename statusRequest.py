"""
We will request line status for all lines (preferably including buses, nat rail etc.)
from the TFL API.

We will transform this into my desired format, and append it to a file or database.

We will finally set up a script that periodically performs this action (e.g. every 15 minutes)
"""

import requests

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
    we could also ask for national rail, river bus and bus services"""
    tube_status_url = 'https://api.tfl.gov.uk/Line/Mode/tube,overground,dlr/Status'
    response = requests.get(tube_status_url, params=credentials)
    tube_status_json = response.json()
    return tube_status_json
