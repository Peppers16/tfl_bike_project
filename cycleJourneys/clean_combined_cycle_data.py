# Based on findings from journeys_initial_exploration, this script takes the combined cycle journey data as input
# and exports a cleansed version of the file, having applied various data cleansing steps to the data

import numpy as np
import pandas as pd

input_csv = r'..\data\cycle_journeys\JourneysDataCombined.csv'
output_csv = r'..\data\cycle_journeys\JourneysDataCombined_CLEANSED.csv'


def correct_start_date_errors(df):
    """ Overwrites start_date in the dataframe.
    Dataset contains start dates in 1900. In such cases, the complimenting end date column appears
    to be correct, as well as the duration. This function attempts to fix the implausible start dates.
    """
    df['Start Date'].where(
        # If start date is after 2012 we can trust it. If end date is before 2012, the fix won't work
        (df['Start Date'] >= '2012') | (df['End Date'] < '2012')
        # else: correct start_date using end date
        , df['End Date'] - pd.to_timedelta(df['Duration'], unit='s')
        , axis=0
        , inplace=True
     )
    return df


def correct_0_end_date_stations(df):
    """ overwrites 'End Date' and 'EndStation Id' and 'Duration' columns in the dataframe.
    In 2012/2013, missing end dates and missing end stations are encoded as 1970-01-01 and 0, respectively.
    This function replaces those cases with NaT and NaN
    """

    # Replace 1970 End Dates with NaT
    df['End Date'].where(
        df['End Date'] >= '2012'
        , pd.NaT
        , axis=0
        , inplace=True
    )

    df['Duration'].where(
        (df['End Date'] >= '2012') & (df['Duration'] >= 0)
        , np.NaN
        , axis=0
        , inplace=True
    )

    df['EndStation Id'].where(
        df['EndStation Id'] != 0
        , np.NaN
        , inplace=True
    )

    return df


def correct_suspect_enddates(df, tolerance=60):
    """ overwrites 'End Date' column in the dataframe.

    There appears to be an issue where end-dates are inconsistent with duration, especially when a journey passes over
    midnight.
    This function updates End Date to be start date + duration, if end_date - start_date is more than 'tolerance'
    seconds out from the stated duration
    """
    duration_from_dates = (df['End Date'] - df['Start Date']) / np.timedelta64(1, 's')
    diff = duration_from_dates - df['Duration']

    # where dif
    df['End Date'].where(
        abs(diff) <= tolerance | df['End Date'].isna()
        , df['Start Date'] + pd.to_timedelta(df['Duration'], unit='s')
        , axis=0
        , inplace=True
    )

    return df


transformations = [correct_start_date_errors, correct_0_end_date_stations, correct_suspect_enddates]


def main(input_csv, output_csv, transformations):
    df_iter = pd.read_csv(input_csv, header=0, sep=',', parse_dates=['Start Date', 'End Date']
                           ,infer_datetime_format=True, chunksize=1000000)
    mode, header = 'w+', True  # for first chunk
    for df_chunk in df_iter:
        # apply transformations
        for f in transformations:
            df_chunk = f(df_chunk)
        df_chunk.to_csv(output_csv, mode=mode, index=False, header=header)
        mode, header = 'a', False  # all subsequent chunks
    print("Done!")


if __name__ == '__main__':
    main(input_csv, output_csv, transformations)
