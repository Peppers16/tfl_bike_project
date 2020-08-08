# This script should no longer be run interactively. It is meant to be called by tfl_project.create_sqlite_database.py

# This script is intended to be run AFTER station_data_to_sql.py
# It uploads some metadata about stations to the SQLite database
# Script was originally written as an interactive notebook, and has been converted to a script.

import sqlite3
import pickle
import pandas as pd
from numpy import isnan

import tfl_project.tfl_api_logger.bikeStationStatus as bikeStationStatus

DBPATH = "data/bike_db.db"


def main():
    # connect to sqlite database
    db = sqlite3.connect(DBPATH)

    # Bikepoint Station Data
    bikepointid_to_commonname = pickle.load(open(r"data\cycle_journeys\bikepointid_to_commonname.p", "rb"))
    bikepointid_to_latlongs = pickle.load(open(r"data\cycle_journeys\bikepointid_to_latlongs.p", "rb"))

    # Manually excluding one timestamp where only three bikepoints were recorded?
    station_fill = pd.read_sql_query("""
        SELECT
            timestamp, bikepoint_id, docked, empty, docked + empty AS capacity
        FROM
            station_fill
        WHERE
            timestamp != "2020-06-22 10:00:00"
        """, db, parse_dates=['timestamp'])

    bp_capacities = station_fill.pivot_table(index='bikepoint_id', columns='timestamp', values='capacity')

    # Start to merge station attributes
    bp_summaries = pd.merge(
        bp_capacities.max(axis=1).rename('max_capacity')
        ,bp_capacities.median(axis=1).rename('median_capacity')
        ,right_index=True
        ,left_index=True)

    # So, both max and median give reliable summaries for bikepoint capacity, but in some cases median is slightly lower
    # (e.g. due to docks being out of action?).
    # Little bit of a decision on which to use:
    # * max gives a reflection of the number of physical docks in the system.
    # * median gives a 'fairer' reflection of the number that were actually available to TFL for much of the period.

    # So: Except all stations to have a capacity between 10 and 64

    # Merge additional data:

    # Merge common name (i.e. english description)
    bp_summaries = bp_summaries.merge(
        pd.DataFrame.from_dict(bikepointid_to_commonname, orient='index').rename(columns={0: 'common_name'})
        ,how='outer'
        ,left_index=True
        ,right_index=True
    )

    # Merge geographic coordiantes
    bp_summaries = bp_summaries.merge(
        pd.DataFrame.from_dict(bikepointid_to_latlongs, orient='index').rename(columns={0: 'latitude', 1:'longitude'})
        ,how='outer'
        ,left_index=True
        ,right_index=True
    )

    # Where possible, I will **plug missing data with a more recent call from the API**.
    # I'll start by re-using some functions from my existing module which is used for logging station data

    bike_json = bikeStationStatus.request_station_status(
        credentials=bikeStationStatus.read_api_credentials('tfl_api_logger/apiCredentials.txt')
    )

    # Impute missing values with API data
    # for convenience I take a copy of the subset of problem rows
    # The actual fix edits the original bp_summaries dataframe
    to_fix = bp_summaries[bp_summaries.isnull().any(axis=1)]
    ids_to_fix = ['BikePoints_' + str(id_) for id_ in to_fix.index]

    for station in bike_json:
        if station['id'] in ids_to_fix:
            found_id = int(station['id'][11:])
            fixing_row = to_fix.loc[found_id]
            if not isinstance(fixing_row['common_name'], str):
                print(f"Adding common_name to bikepoint {found_id}")
                bp_summaries.loc[found_id, 'common_name'] = station['commonName']
            if isnan(fixing_row['latitude']):
                print(f"Adding co-ordinates to bikepoint {found_id}")
                bp_summaries.loc[found_id,'latitude'] = station['lat']
                bp_summaries.loc[found_id,'longitude'] = station['lon']
            if isnan(fixing_row['median_capacity']):
                print(f"Adding capacities to {found_id}")
                bp_summaries.loc[found_id,'median_capacity'] = [p['value'] for p in station['additionalProperties'] if p['key'] == 'NbDocks'][0]
                bp_summaries.loc[found_id,'max_capacity'] = [p['value'] for p in station['additionalProperties'] if p['key'] == 'NbDocks'][0]

    # We are now left with 5 missing stations. Manual inspection suggests these have all been closed / inactive in
    # recent months. Question is: how to get their location...?
    #
    # Options:
    # * Impute a centroid co-ordinate
    # * Infer a co-ordiate based on journey durations from other stations (smart but a lot of effort for 5 stations).
    # * Replace these stations with the null -1 station ID
    # * Our distnace metric could be based on average duration rather than euclidean distance. This might actually be a
    # more sensible approach.

    bp_summaries.index.name = 'bikepoint_id'
    # Upload to SQLite database
    bp_summaries.to_sql('station_metadata'
                        ,db
                        ,if_exists='fail'
                        ,index=True
                        ,dtype={
                            'bikepoint_id': 'INT'
                            , 'max_capacity': 'INT'
                            , 'median_capacity': 'INT'
                            , 'common_name': 'STRING'
                            , 'latitude': 'REAL'
                            , 'longitude': 'REAL'
                        }
                        )

    db.execute("""
        CREATE UNIQUE INDEX "meta_id" ON "station_metadata" ("bikepoint_id");
    """)

    db.close()
    print('done')


def add_avg_5am_docked(pre_covid=True):
    extra_where = ""
    if pre_covid:
        extra_where = "AND timestamp <= '2020-03-15'"
    db = sqlite3.connect(DBPATH)
    db.execute("ALTER TABLE station_metadata ADD COLUMN avg_5am_docked INTEGER;")
    db.execute(f"""
        WITH avg_5ams AS (
            SELECT
                bikepoint_id
                ,CAST(ROUND(AVG(docked)) AS INTEGER) AS docked_5am
            FROM 
                station_fill
            WHERE 
                hour = 5
                AND weekday = 1
                AND TIME(timestamp) = '05:00:00'
                {extra_where}
            GROUP BY 1
            ) 
        
        UPDATE station_metadata
        SET avg_5am_docked = (
            SELECT docked_5am
            FROM avg_5ams
            WHERE station_metadata.bikepoint_id = avg_5ams.bikepoint_id
            )
    ;""")
    db.close()
