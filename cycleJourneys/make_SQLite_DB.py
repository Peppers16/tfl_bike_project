import sqlite3
import pandas as pd

# RUN THIS SCRIPT FROM THE INTERPRETER WITH tflProject AS THE PWD

db = sqlite3.connect(r'bike_db.db')
clean_journeys = r'..\data\cycle_journeys\JourneysDataCombined_CLEANSED.csv'

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
               );
            """)

for chunk in pd.read_csv(clean_journeys, header=0, sep=',', parse_dates=['Start Date', 'End Date'],
                         dayfirst=True, infer_datetime_format=True, chunksize=1000000):
    chunk["year"] = chunk["Start Date"].dt.year
    chunk["month"] = chunk["Start Date"].dt.month
    chunk["hour"] = chunk["Start Date"].dt.hour
    chunk["weekday"] = chunk["Start Date"].dt.weekday
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
db.close()

# MOVE FILE TO data/