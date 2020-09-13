import sqlite3
import pandas as pd
from os import rename
from pathlib import Path
import numpy as np

from tfl_project.database_creation.station_data_to_sql import table_exists

# This script should no longer be run interactively. It is meant to be called by tfl_project.create_sqlite_database.py
clean_journeys = Path('tfl_project/data/cycle_journeys/JourneysDataCombined_CLEANSED.csv')
database = Path('tfl_project/data/bike_db.db')


def main():
    if table_exists('journeys'):
        print("journeys table already exists. This is a slow step so will be skipped. Manually drop table if desired")
        return
    db = sqlite3.connect(database)

    db.execute(f"""CREATE TABLE journeys (
                   "Rental Id" INTEGER
                   ,"Duration" INTEGER
                   ,"Bike Id" INTEGER
                   ,"End Date" DATETIME
                   ,"EndStation Id" INTEGER
                   ,"Start Date" DATETIME
                   ,"StartStation Id" INTEGER
                   ,"year" INTEGER
                   ,"month" INTEGER
                   ,"hour" INTEGER
                   ,"day_of_week" INTEGER
                   ,"minute_of_day" INTEGER
                   ,"weekday_ind" INTEGER CHECK(weekday_ind IN (0,1))
                   ,FOREIGN KEY ("StartStation Id") REFERENCES station_metadata(bikepoint_id)
                   ,FOREIGN KEY ("EndStation Id") REFERENCES station_metadata(bikepoint_id)
                   );
                """)

    for chunk in pd.read_csv(clean_journeys, header=0, sep=',', parse_dates=['Start Date', 'End Date'],
                             dayfirst=True, infer_datetime_format=True, chunksize=1000000):
        chunk["year"] = chunk["Start Date"].dt.year
        chunk["month"] = chunk["Start Date"].dt.month
        chunk["hour"] = chunk["Start Date"].dt.hour
        chunk["day_of_week"] = chunk["Start Date"].dt.weekday
        chunk["minute_of_day"] = chunk["hour"]*60 + chunk["Start Date"].dt.minute
        chunk["weekday_ind"] = np.where(chunk["day_of_week"] <= 4, 1, 0)
        chunk.to_sql("journeys", db, if_exists="append", index=False)

    db.execute("CREATE INDEX year ON journeys(year)")
    db.execute("CREATE INDEX month ON journeys(month)")
    db.execute("CREATE INDEX hour ON journeys(hour)")
    db.execute("CREATE INDEX weekday ON journeys(weekday_ind)")
    db.execute("""CREATE INDEX start_station ON journeys("StartStation Id")""")
    db.execute("""CREATE INDEX end_station ON journeys("EndStation Id")""")
    db.execute("""CREATE INDEX bike_id ON journeys("Bike Id")""")
    db.execute("""CREATE INDEX date_hour ON journeys(year, month, "weekday", hour)""")
    db.execute("""CREATE INDEX start_end ON journeys("StartStation Id", "EndStation Id")""")
    db.execute("""CREATE INDEX minute ON journeys(minute_of_day)""")
    db.execute("""CREATE INDEX startid_weekday ON journeys("StartStation Id", weekday_ind)""")
    db.execute("""CREATE INDEX year_weekday_ind ON journeys("year", weekday_ind)""")
    # Slow but helps the optimizer to prioritize filtering by minute.
    db.execute("""ANALYZE journeys""")
    db.close()

    print("journey data finished uploading")


if __name__ == '__main__':
    main()
