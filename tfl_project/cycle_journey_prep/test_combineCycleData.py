from tfl_project.cycle_journey_prep.combineCycleData import *
from pandas import DataFrame
from numpy import nan, isnan, any
from pathlib import Path

in_directory = Path('data/cycle_journeys')


def test_pop_station():
    test_df = DataFrame({'foo': [1, 2, 3, 2, 1], 'bar': ['one', 'two', 'three', 'two', 'one']})
    out_df, key_vals = pop_station(test_df, key_col='foo', description_col='bar')
    assert 'bar' not in out_df.columns
    assert 'bar' in test_df.columns
    assert (out_df['foo'] == test_df['foo']).all()
    assert len(out_df) == 5
    assert len(key_vals) == 3
    assert (1, 'one') in key_vals
    test_df2 = DataFrame({'foo': [1, 2, 3, 2, 1, nan], 'bar': ['one', 'two', 'three', 'two', 'one', nan]})
    out_df2, key_vals2 = pop_station(test_df2, key_col='foo', description_col='bar')
    # filter out nans
    assert not any([isnan(tup[0]) for tup in key_vals2])


def test_keyvals_to_df():
    _, key_vals = pop_station(DataFrame({'foo': [1, 2, 3, 2, 1], 'bar': ['one', 'two', 'three', 'two', 'one']})
                              , key_col='foo', description_col='bar')
    out_df = keyvals_to_df(key_vals)
    assert isinstance(out_df, DataFrame)
    assert out_df.columns.tolist() == ['Station ID', 'Station Name']
    assert len(out_df) == 3
    assert 1 in out_df['Station ID']
    assert 'one' == out_df.loc[out_df['Station ID'] == 1, 'Station Name'].values


def test_determine_columns():
    file = "05JourneyDataExtract01May2016-17May2016.csv"
    # This simulates user input of 'yes' in response to question
    assert len(determine_columns(in_directory, file, 9)) == 9
