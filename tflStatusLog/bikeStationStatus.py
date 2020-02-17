from logging_functions import *
import requests
import datetime

credentials_file = 'apiCredentials.txt'
csv_file = '/mnt/ntfsHDD/tfl_logging/bikepoint_statuses.csv'

def extract_station_data(station_data, timestamp):
    station_id = station_data['id']
    for d in station_data['additionalProperties']:
        if d['key'] == 'NbBikes':
            docked_bikes = d['value']
        elif d['key'] == 'NbEmptyDocks':
            empty_docks = d['value']
    return [timestamp, station_id, int(docked_bikes), int(empty_docks)]


def request_station_status(credentials):
    station_status_url = 'https://api.tfl.gov.uk/bikepoint'
    response = requests.get(station_status_url, params=credentials)
    tube_status_json = response.json()
    return tube_status_json


def create_csv_if_needed(csv_file):
    headers = ['timestamp', 'station_id', 'docked_bikes', 'empty_docks']
    if not os.path.exists(csv_file):
        create_csv(csv_out=csv_file, headers=headers)


if __name__ == '__main__':
    credentials = read_api_credentials(credentials_file)
    timestamp = datetime.datetime.now()
    data = request_station_status(credentials)
    create_csv_if_needed(csv_file)
    for station in data:
        row = extract_station_data(station, timestamp)
        append_to_csv(csv_file, row)

