from bs4 import BeautifulSoup
import codecs
import re
import requests
import time
import os
from pandas import read_csv, concat, DataFrame, Int64Dtype
from numpy import nan, object, datetime64
import csv as csv

# Note the pyarrow dependency seems to need to be installed by pip, not conda

page_file = 'cycling.data.tfl.gov.uk.html'
regex = "^https://cycling.data.tfl.gov.uk/usage-stats/.*Journey.*Data.*.csv"
output_directory = r"data/cycle_journeys/"
seconds_per_call = 60/300
expected_n_cols = 9


def download_csvs_matching_regex(page_file, regex, output_directory, seconds_per_call):
    # Extract soup from the html page you saved previously
    with codecs.open(page_file) as html:
        soup = BeautifulSoup(html, features="html.parser")

    # List of the urls themselves, matching the regex parameter
    all_urls = [a_tag['href'] for a_tag in soup.findAll('a', attrs={'href': re.compile(regex)})]
    # duplicate: remove
    all_urls.remove('https://cycling.data.tfl.gov.uk/usage-stats/01b%20Journey%20Data%20Extract%2024Jan16-06Feb16.csv')

    # request then save each CSV file
    for url in all_urls:
        output_name = url[url.find('usage-stats/') + 12:]  # takes the csv portion of the url
        if os.path.isfile(output_directory + output_name):
            print("Note: skipped existing file " + output_directory + output_name)
        else:
            # download each CSV, but ensuring no more than 300 hits per minute
            starttime = time.time()
            print('requesting', url)
            file = requests.get(url)
            # Write to CSV
            with open(output_directory + output_name, 'w+', newline='') as output:
                output.write(file.text)
            print('written to', output_directory + output_name)
            # Wait if necessary
            time_taken = time.time() - starttime
            if time_taken < seconds_per_call:
                time.sleep(seconds_per_call - time_taken)

    print('done!')


# These are all functions used in the read_csvs_generator
def get_csv_headers(in_directory, csv_name):
    with open(in_directory + csv_name, 'r', newline='') as csv_file:
        reader = csv.reader(csv_file, delimiter=',', quotechar='"')
        line = reader.__next__()
        return line


def ask_cols_to_use(header, expected):
    print("HEY! unexpected header length of", len(header))
    print(header)
    extra_columns = header[expected:]
    if all([col == '' for col in extra_columns]):
        print("All extras are blank columns. Correcting automatically...")
        return header[:expected]
    correct_columns = header.copy()
    while len(correct_columns) != expected:
        delete = input('please name one column to drop:')
        correct_columns.remove(delete)
    return correct_columns


def determine_columns(in_directory, csv_name, expected):
    header = get_csv_headers(in_directory, csv_name)
    if len(header) == expected:
        return header
    else:
        return ask_cols_to_use(header, expected)


def read_csvs_generator(in_directory, expected):
    """Returns a generator which searches for all .csv files in the input directory and, returns each of them as a df
    This is more efficient for use in pd.concat() than reading all the CSVs in bulk"""
    file_list, file_sizes = scan_files(in_directory)
    start_time = time.time()
    for i, file in enumerate(file_list):
        if file.endswith('.csv'):
            if i % 10 == 0:  # give time update
                time_report(start_time, i, file_sizes)
            use_cols = determine_columns(in_directory, file, expected)
            print(str(i+1)+'/'+str(len(file_list)), file)
            yield file, read_csv(in_directory + file
                                 , usecols=use_cols
                                 # , infer_datetime_format=True, parse_dates=[3, 6], cache_dates=True
                                 , index_col=0, encoding="ISO-8859-1", dtype='str')  # ISO encoding needed to avoid errors


def scan_files(in_directory):
    file_list = [f for f in os.listdir(in_directory) if f.endswith('.csv')]
    file_sizes = [os.stat(in_directory+f).st_size for f in file_list]
    return file_list, file_sizes


def time_report(start_time, i, file_sizes):
    """provides a report of elapsed time and an estimate of remaining time.
    file_sizes is a list of each file's size in the list"""
    elapsed = time.time() - start_time
    total_bytes = sum(file_sizes)
    done_bytes = sum(file_sizes[:i-1])
    time_p_byte = elapsed / done_bytes
    est_remaining = (total_bytes - done_bytes) * time_p_byte
    print('\t{:1.1f} elapsed, estimated remaining time: {:1.1f}'.format(elapsed / 60, est_remaining / 60))


def pop_station(df, key_col, description_col):
    """Function is designed to remove a description column and extract (key,value) pairs instead for use as metadata.
    It returns the df with 'description_col' dropped, and a set of all identified key_value pairs"""
    key_vals = set(zip(df[key_col], df[description_col]))
    # filter nans from set
    key_vals = set(filter(lambda tup: nan not in tup and '' not in tup, key_vals))
    df = df.drop(description_col, axis=1)
    return df, key_vals


def keyvals_to_df(key_vals):
    return DataFrame(data=key_vals, columns=['Station ID', 'Station Name'])


def process_st_names(df, keyvaluepairs):
    # firstly, scan for problem columns and fix if needed:
    df = df.rename(columns={
        'Duration_Seconds': 'Duration'
        ,'End Station Id': 'EndStation Id'
        ,'End Station Name': 'EndStation Name'
        ,'Start Station Id': 'StartStation Id'
        ,'Start Station Name': 'StartStation Name'
        ,'EndStation Logical Terminal': 'EndStation Id'
        ,'StartStation Logical Terminal': 'StartStation Id'
    })
    # secondly: drop the id columns and add any new key,value pairs to the set
    df, kvp1 = pop_station(df, 'EndStation Id', 'EndStation Name')
    df, kvp2 = pop_station(df, 'StartStation Id', 'StartStation Name')
    keyvaluepairs = keyvaluepairs | kvp1
    keyvaluepairs = keyvaluepairs | kvp2
    return df, keyvaluepairs


def combine_csvs(in_directory, file_out, expected_n_cols, compression='gzip', drop_st_names=True):
    """Reads csvs in the directory and combines them into one file using pandas. Appends to the file, so does not
    take place entirely in memory.
    If drop_st_names=True then returns all key-value-pairs identified. Otherwise returns None"""
    if os.path.exists(in_directory+file_out):
        raise FileExistsError(f'The output file: {file_out} already exists')
    keyvaluepairs = set()
    header = True  # first pass only
    problem_csvs = []
    for csvname, df in read_csvs_generator(in_directory, expected_n_cols):
        if drop_st_names:
            try:
                df, keyvaluepairs = process_st_names(df, keyvaluepairs)
            except:
                print(f"! {csvname} could not be processed.")
                problem_csvs.append((csvname, df))
                continue
        # append resulting df to the output csv
        df.to_csv(in_directory + file_out, mode='a', header=header, compression=compression)
        header = False  # after first iteration exclude headers
    # make a final pass for the problem CSVs to see if they can be fixed
    if len(problem_csvs) > 0:
        for csv, _ in problem_csvs:
            print(f'NOTE: {csv} was not appended')
    if drop_st_names:
        return keyvals_to_df(keyvaluepairs)
    print('DONE!')


if __name__ == '__main__':
    in_directory = r"../data/cycle_journeys/"
    file_out = 'JourneysDataCombined.csv'
    stations_out = 'Station Lookup.csv'

    # expected_cols = ['Rental Id', 'Duration', 'Bike Id', 'End Date', 'EndStation Id', 'EndStation Name', 'Start Date'
    #                  , 'StartStation Id', 'StartStation Name']
    stations = combine_csvs(in_directory, file_out, expected_n_cols, compression='infer',  drop_st_names=True)
    # also save the station names as metadata
    stations.to_csv(in_directory+stations_out, index=False)
