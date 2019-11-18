from cycleJourneys.combineCycleData import *
from pandas import DataFrame
from numpy import nan, isnan, any

in_directory = r"F:/Josh Documents (HDD)/tfl_project_csvs/cycle_journeys/"

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


def test_fix_ESLT_issue():
    bad_csv = '21JourneyDataExtract31Aug2016-06Sep2016.csv'
    good_csv = '99JourneyDataExtract28Feb2018-06Mar2018.csv'
    bad_df = read_csv(in_directory + bad_csv, index_col=0, encoding="ISO-8859-1", dtype='str', nrows=10)
    good_df = read_csv(in_directory + good_csv, index_col=0, encoding="ISO-8859-1", dtype='str')
    _, key_vals = pop_station(good_df, 'EndStation Id', 'EndStation Name')
    assert 'EndStation Logical Terminal' in bad_df.columns
    assert 'EndStation Logical Terminal' not in good_df.columns
    fixed_df = fix_ESLT_issue(df=bad_df, key_vals=key_vals, bad_id='EndStation Logical Terminal'
                              ,name_column='EndStation Name',desired_id= 'EndStation Id')
    assert 'EndStation Logical Terminal' not in fixed_df.columns
    assert (fixed_df[fixed_df['EndStation Name'] == 'Bermondsey Street, Bermondsey']['EndStation Id'] == '321').all()
