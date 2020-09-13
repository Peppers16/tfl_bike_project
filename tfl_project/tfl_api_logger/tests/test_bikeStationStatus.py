import json
import os
import datetime
from pathlib import Path
from tfl_project.tfl_api_logger.bikeStationStatus import *
from tfl_project.tfl_api_logger.logging_functions import *


test_json_file = str(Path('tfl_api_logger/tests/json_test.json'))
test_output_csv = str(Path('tfl_api_logger/tests/test_output_csv.csv'))
credentials_file = str(Path('tfl_api_logger/apiCredentials.txt'))

# cleanup
if Path(test_output_csv).exists():
    Path(test_output_csv).unlink()


with open(test_json_file) as json_file:
    data = json.load(json_file)


def test_create_csv():
    test_headers = ['timestamp', 'station_id', 'docked_bikes', 'empty_docks']
    if os.path.exists(test_output_csv):
        os.remove(test_output_csv)
    create_csv_if_needed(csv_file=test_output_csv)
    assert os.path.exists(test_output_csv)


def test_extract_station_data():
    row_data = extract_station_data(data[0], datetime.datetime.now())
    assert row_data[1:] == ['BikePoints_1', 19, 0]


def test_get_station_status():
    json = request_station_status(credentials_file)
