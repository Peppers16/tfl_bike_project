import pickle
from pathlib import Path

from tfl_project.tfl_api_logger.bikeStationStatus import request_station_status
from tfl_project.tfl_api_logger.logging_functions import read_api_credentials

credentials_file = Path('tfl_project/tfl_api_logger/apiCredentials.txt')
out_dir = Path('tfl_project/data/tfl_lookups')


def create_tfl_station_lookups(credentials_file=credentials_file):
    """This makes a request to the bikepoints API, dumps some metadata to pickles
    This is a bit of a legacy from before I was working in SQL.

    returns a bikepoint_id to common_name lookup
     and a terminal_name to common_name lookup
     and a common_name to bikepoint_id lookup
    """
    credentials = read_api_credentials(credentials_file)
    response_json = request_station_status(credentials)
    # list bikepoint_ids
    bikepoint_ids = [int(d['id'][11:]) for d in response_json]
    # list terminal names
    terminal_names = []
    for d in response_json:
        for prop in d['additionalProperties']:
            if prop['key'] == 'TerminalName':
                terminal_names.append(int(prop['value']))
    # fetch common names (i.e. descriptions)
    common_names = [d['commonName'] for d in response_json]
    # for convenience later: look up lat longs
    latlongs = [(float(d['lat']), float(d['lon'])) for d in response_json]
    # zip into dictionary lookups
    bp_to_name = dict(zip(bikepoint_ids, common_names))
    tn_to_bp = dict(zip(terminal_names, bikepoint_ids))
    bp_to_latlongs = dict(zip(bikepoint_ids, latlongs))
    return bp_to_name, tn_to_bp, bp_to_latlongs


def dump_tfl_lookups(bp_to_name, tn_to_bp, bp_to_latlongs, out_dir):
    pickle.dump(bp_to_name, open(out_dir / 'bikepointid_to_commonname.p', 'wb'))
    pickle.dump(bp_to_latlongs, open(out_dir / 'bikepointid_to_latlongs.p', 'wb'))
    pickle.dump(tn_to_bp, open(out_dir / 'bikepointid_to_terminal_name.p', 'wb'))
    print("Dumped lookups as pickle files!")


def main(out_dir: Path = out_dir):
    if not out_dir.exists():
        out_dir.mkdir()

    cn_dir = out_dir / 'bikepointid_to_commonname.p'
    ll_dir = out_dir / 'bikepointid_to_latlongs.p'
    tn_dir = out_dir / 'bikepointid_to_terminal_name.p'

    for f in [cn_dir, ll_dir, tn_dir]:
        if f.exists():
            print(f"{str(f)} already exists. Aborting")
            return
    print("fetching lookups from TFL API")
    bp_to_name, tn_to_bp, bp_to_latlongs = create_tfl_station_lookups()
    print("dumping to pickle files")
    dump_tfl_lookups(bp_to_name, tn_to_bp, bp_to_latlongs, out_dir)
    print(f"pickle files dumped to {str(out_dir)}")


if __name__ == '__main__':
    main()