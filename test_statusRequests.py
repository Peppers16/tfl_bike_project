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

