import sqlite3
import pandas as pd
from os import rename

# RUN THIS SCRIPT FROM THE INTERPRETER WITH tflProject\cycleJourneys AS THE PWD

db = sqlite3.connect(r'bike_db.db')
clean_journeys = r'..\data\cycle_journeys\JourneysDataCombined_CLEANSED.csv'
destination_location = r'..\data\bike_db.db'

c = db.cursor()
c.execute("""CREATE TABLE journeys (
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
               ,"weekday" INTEGER
               ,"minute_of_day" INTEGER
               );
            """)

for chunk in pd.read_csv(clean_journeys, header=0, sep=',', parse_dates=['Start Date', 'End Date'],
                         dayfirst=True, infer_datetime_format=True, chunksize=1000000):
    chunk["year"] = chunk["Start Date"].dt.year
    chunk["month"] = chunk["Start Date"].dt.month
    chunk["hour"] = chunk["Start Date"].dt.hour
    chunk["weekday"] = chunk["Start Date"].dt.weekday
    chunk["minute_of_day"] = chunk["hour"]*60 + chunk["Start Date"].dt.minute
    chunk.to_sql("journeys", db, if_exists="append", index=False)


db.execute("CREATE INDEX year ON journeys(year)")
db.execute("CREATE INDEX month ON journeys(month)")
db.execute("CREATE INDEX hour ON journeys(hour)")
db.execute("CREATE INDEX weekday ON journeys(weekday)")
db.execute("""CREATE INDEX start_station ON journeys("StartStation Id")""")
db.execute("""CREATE INDEX end_station ON journeys("EndStation Id")""")
db.execute("""CREATE INDEX bike_id ON journeys("Bike Id")""")
db.execute("""CREATE INDEX date_hour ON journeys(year, month, "weekday", hour)""")
db.execute("""CREATE INDEX start_end ON journeys("StartStation Id", "EndStation Id")""")
db.execute("""CREATE INDEX minute ON journeys(minute_of_day)""")
# Slow but helps the optimizer to prioritize filtering by minute.
db.execute("""ANALYZE journeys""")
db.close()

# MOVE FILE TO data/
rename('bike_db.db', destination_location)
print("bike_db.db was moved to data/")