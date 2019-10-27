from statusRequest import *

def test_read_api_credentials():
    read_api_credentials('apiCredentials.txt')
    assert credentials['app_id'] != ''
    assert credentials['app_key'] != ''


def test_request_meta_modes():
    modes = request_meta_modes()
    assert 'tube' in modes


def test_request_meta_severitycodes():
    sev_codes = request_meta_severitycodes()
    assert 'severityLevel' in sev_codes[0].keys()


def test_request_tube_status():
    tube_status = request_tube_status()
    assert len(tube_status) > 1
    for line in tube_status:
        assert line['modeName'] in ['tube', 'overground', 'dlr']


def test_create_and_append_csv():
    create_csv('test.csv', ['test1', 'test2'])
    assert os.path.isfile('test.csv')
    append_to_csv('test.csv', ['foo', 'bar'])
    os.remove('test.csv')


def test_extract_status_row():
    statuses = request_tube_status()
    statusrow = extract_status_row(datetime.datetime.now(), statuses[0])
    assert len(statusrow) > 1
