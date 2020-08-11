# It is likely that data/bike_db.db already exists (made by make_SQLite_DB.py).
# If so, you will want to connect to the existing dababase rather than make another one.

# This script should no longer be run interactively. It is meant to be called by tfl_project.create_sqlite_database.py

import os
import warnings
import pandas as pd
from numpy import int64
import sqlite3
from pathlib import Path

# PWD for this script will be set to data/
station_csv = Path('data/Bikepoints/bikepoint_statuses.csv')
database = Path('data/bike_db.db')
table = 'station_fill'


def read_format_station_csv(station_csv):
    """Read station csv to pd.dataframe and reformat it"""
    df = pd.read_csv(station_csv)
    # Round (generally by a few seconds) to the nearest quarter hour, to give a consistent index
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='%Y-%m-%d %H:%M:%S.%f')
    df['timestamp'] = df['timestamp'].dt.round('15min')
    # Convert station_id to integer
    df['station_id'] = df['station_id'].str[len('BikePoints_'):].astype(int64)
    df.columns = ['timestamp', 'bikepoint_id', 'docked', 'empty']
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.weekday
    return df


def table_exists(table):
    """Check if station table exists already"""
    db = sqlite3.connect(database)
    c = db.cursor()
    c.execute(f''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='{table}' ''')
    if c.fetchone()[0] == 1:
        c.close()
        return True
    else:
        c.close()
        return False


def create_station_table():
    db = sqlite3.connect(database)
    c = db.cursor()
    q = f"""CREATE TABLE {table} (
                   "timestamp" DATETIME NOT NULL
                   ,"bikepoint_id" INTEGER  NOT NULL
                   ,"docked" INTEGER NOT NULL CHECK(docked >= 0)
                   ,"empty" INTEGER NOT NULL CHECK(empty >= 0)
                   ,"hour" INTEGER NOT NULL 
                   ,"day_of_week" INTEGER NOT NULL
                   );
                """
    c.execute(q)
    c.close()


def drop_table(table):
    db = sqlite3.connect(database)
    c = db.cursor()
    q = f"""DROP TABLE {table} ;"""
    c.execute(q)
    c.close()


def df_to_sql_upload(df):
    db = sqlite3.connect(database)
    df.to_sql(table, db, if_exists="append", index=False)
    db.close()


def index_table():
    db = sqlite3.connect(database)
    db.execute(f"CREATE INDEX stn_hour ON {table}(hour)")
    db.execute(f"CREATE INDEX stn_wkday ON {table}(day_of_week)")
    db.close()


def main():
    # Check and recreate SQLite table if it already exists
    if not table_exists(table=table):
        print(f'{table} does not exist in database. Creating...')
    else:
        print(f'{table} already exists! Dropping then recreating...')
        drop_table(table=table)
    create_station_table()
    # Read csv then upload it to SQL table
    df = read_format_station_csv(station_csv)
    print('DataFrame read, with format:')
    print(df.head())
    print('Uploading to SQLite DB')
    df_to_sql_upload(df)
    print('creating indexes')
    index_table()
    print('Done!')


if __name__ == '__main__':
    main()
