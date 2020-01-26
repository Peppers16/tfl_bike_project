from logging_functions import *
import requests
import datetime

credentials_file = 'apiCredentials.txt'
credentials = read_api_credentials(credentials_file)
csv_file = '/mnt/ntfsHDD/tfl_logging/bikepoint_statuses.csv'

def extract_station_data(station_data, timestamp):
    station_id = station_data['id']
    for d in station_data['additionalProperties']:
        if d['key'] == 'NbBikes':
            docked_bikes = d['value']
        elif d['key'] == 'NbEmptyDocks':
            empty_docks = d['value']
    return [timestamp, station_id, int(docked_bikes), int(empty_docks)]


def request_station_status():
    station_status_url = 'https://api.tfl.gov.uk/bikepoint'
    response = requests.get(station_status_url, params=credentials)
    tube_status_json = response.json()
    return tube_status_json


def create_csv_if_needed(csv_file):
    headers = ['timestamp', 'station_id', 'docked_bikes', 'empty_docks']
    if not os.path.exists(csv_file):
        create_csv(csv_out=csv_file, headers=headers)


def singleRequest(log_to_google=True, log_to_csv=False):
    """ This fires a single request instead of a timed loop. This option is when using a scheduler like Cron.
     By default, logs to Google and also logs to CSV """
    data = request_and_format()
    print('Requested: ' + time.ctime())
    # Record to CSV if requested
    if log_to_csv:
        try:
            log_now_csv(csv_file)
        except:
            print("Warning: Failed to write to CSV")
    # Record to Google if requested (make 3 attempts)
    if log_to_google:
        upload_attempts = 0
        successful = False
        while not successful and upload_attempts < 3:
            try:
                googleSheetsAccess.log_to_google(data, google_spreadsheet_id)
                successful = True
            except:
                print("Warning: Failed to upload to Google")
                upload_attempts += 1
                time.sleep(3)


if __name__ == '__main__':
    timestamp = datetime.datetime.now()
    data = request_station_status()
    create_csv_if_needed(csv_file)
    for station in data:
        row = extract_station_data(station, timestamp)
        append_to_csv(csv_file, row)

