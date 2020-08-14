from tfl_project.cycle_journey_prep.clean_combined_cycle_data import authority_station_list
import pandas as pd
from pathlib import Path

output_csv = Path('data/cycle_journeys/JourneysDataCombined_CLEANSED.csv')


class TestCleanStations:
    def test_authority_station_list(self):
        auth_list = authority_station_list()
        # these are stations that were missing before
        assert 95 in auth_list
        assert 65 in auth_list
        assert 320 in auth_list
        assert 808 in auth_list
        assert 794 in auth_list

    def test_output_csv(self):
        df = pd.read_csv(output_csv, header=0, sep=',', parse_dates=['Start Date', 'End Date']
                    ,dayfirst=True, infer_datetime_format=True, nrows=2000)
        assert 95 in df["StartStation Id"]
        assert 95 in df["EndStation Id"]