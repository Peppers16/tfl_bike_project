import pickle
import sqlite3
import time
from copy import deepcopy
from pandas import read_sql
from scipy.stats import gumbel_r

from tfl_project.simulation.sim_classes import City, Station


class LondonCreator:
    def __init__(self, min_year=2015, minute_interval=20, exclude_covid=True
                 , additional_sql_filters=""""""):
        """
        Creates a city that emulates the true London BBS, including its stations.

        min_year: First year from which simulation data will be modelled
        minute_interval: The granularity with which data will be summarised. E.g. if 20, the journey demand per
            station will be calculated per every 20-minute interval in a 24 hour period.

        TODO: decide best way to customise simulated versions of London. You could instantiate a LondonCreator
         and manually modify its .london attribute? Or you could pass it parameters in a spreadsheet or similar.
        """
        self.london = City(interval_size=minute_interval)
        self.min_year = min_year
        self.minute_interval = minute_interval
        self.additional_filters = additional_sql_filters
        if exclude_covid:
            self.additional_filters = additional_sql_filters + """ AND "Start Date" <= '2020-03-15'"""

    def select_query_db(self, query):
        dbpath = "data/bike_db.db"
        db = sqlite3.connect(dbpath)
        c = db.cursor()
        c.execute(query)
        rows = c.fetchall()
        db.close()
        return rows

    def df_from_sql(self, query):
        dbpath = "data/bike_db.db"
        db = sqlite3.connect(dbpath)
        try:
            df = read_sql(query, db)
        finally:
            db.close()
        return df

    def populate_tfl_stations(self):
        """
        Takes the new city and adds stations to it which reflect the true TFL BSS.
        Uses a SQLite table, station_metadata, which has already been prepared.
        Adds additional attributes to stations: _latitude, _longitude, _common_name
        """
        print("fetching station metadata")
        rows = self.select_query_db(
            """
            SELECT
                bikepoint_id
                ,max_capacity AS capacity
                ,common_name
                ,latitude
                ,longitude 
            FROM station_metadata
            """
        )
        print("Populating stations")
        for row in rows:
            # TODO: functionality to define the 'docked_init' attributes that we want.
            #  it possible that the sqlite query will not be flexible enough for trying various simulations
            s = Station(capacity=row[1]
                        , docked_init=row[1]//2
                        , st_id=row[0])
            s._latitude = row[3]
            s._longitude = row[4]
            s._common_name = row[2]
            self.london.add_station(s)

    def populate_station_demand_dicts(self):
        print(f"fetching all station demand per {self.minute_interval} minute interval")
        all_demands = self.select_query_db(
            f"""
            WITH subset AS (
                SELECT *
                FROM journeys
                WHERE
                    year >= {self.min_year}
                    AND weekday = 1
                    {self.additional_filters}
            )

            SELECT
                i."StartStation Id"
                ,i.interval
                ,CAST(i.interval_journeys AS REAL) / d.days_in_action / {self.minute_interval} AS avg_journeys_p_minute
            FROM
                (
                    SELECT
                        "StartStation Id"
                        ,(minute_of_day / {self.minute_interval}) * {self.minute_interval} AS interval
                        ,COUNT(*) AS interval_journeys
                    FROM 
                        subset
                    GROUP BY 1,2
                )AS i
                INNER JOIN (
                    SELECT
                        "StartStation Id"
                        ,COUNT(DISTINCT DATE("Start Date")) AS days_in_action
                    FROM 
                        subset
                    GROUP BY 1
                ) AS d
                    ON i."StartStation Id" = d."StartStation Id"     
            """
        )
        print("fetched. Assigning to stations")
        for row in all_demands:
            bikepoint_id, interval, journeys_p_minute = row
            if bikepoint_id in self.london._stations:
                self.london.get_station(bikepoint_id)._demand_dict[interval] = journeys_p_minute

    def populate_station_destination_dicts(self):
        # No Laplace smoothing
        print(f"fetching distribution of destinations per {self.minute_interval} minute interval, per station")
        all_dests = self.select_query_db(
            f"""
            SELECT
                "StartStation Id"
                ,"EndStation Id"
                ,(minute_of_day / {self.minute_interval}) * {self.minute_interval} AS interval
                ,COUNT(*) AS journeys
            FROM
                journeys
            WHERE
                year >= {self.min_year}
                AND weekday = 1
                {self.additional_filters}
            GROUP BY
                1,2,3"""
        )
        print("fetched. Assigning to stations")
        for row in all_dests:
            bikepoint_id, destination_id, interval, journeys = row
            if bikepoint_id in self.london._stations:
                if destination_id in self.london._stations:
                    self.london.get_station(bikepoint_id).add_dest_volume_parameter(
                        interval=interval
                        , destination_id=destination_id
                        , journeys=journeys
                    )

    def populate_station_duration_params(self):
        # This is intensive so populates one origin station at a time
        for start_id in self.london._stations.keys():
            start_time = time.time()
            journey_df = self.df_from_sql(
                f"""
                SELECT
                    "EndStation Id"
                    ,Duration / 60 AS Duration
                FROM
                    journeys
                WHERE
                    "StartStation Id" = {start_id}
                    AND year >= {self.min_year}
                    AND weekday = 1
                    {self.additional_filters}
                """
            )
            print(f"fetched {len(journey_df)} journeys for station {start_id} in {(time.time()-start_time)/60} minutes")
            journey_df.dropna(subset=['Duration'], inplace=True)
            for end_id in journey_df["EndStation Id"].unique():
                durations = journey_df.loc[journey_df["EndStation Id"] == end_id]['Duration'].values
                # creates a tuple of scipy.stats.gumbel_r parameters
                params = gumbel_r.fit(durations)
                # add the distribution parameters to the duration dict
                self.london.get_station(start_id).add_dest_duration_params(destination_id=end_id, params=params)

    def create_london_from_scratch(self):
        print("Creating City using fresh data pulls")
        self.populate_tfl_stations()
        self.populate_station_demand_dicts()
        self.populate_station_destination_dicts()
        self.populate_station_duration_params()
        print("Done!")
        print(".london attribute has been populated using fresh SQL pulls")

    def pickle_city(self, out_dir='london.pickle'):
        out_file = open(out_dir, 'wb')
        pickle.dump(self.london, out_file)
        out_file.close()
        print(f'City saved as {out_dir} for future use. Use load_pickled_city to use it again')

    def load_pickled_city(self, in_dir='london.pickle'):
        in_file = open(in_dir, 'rb')
        self.london = pickle.load(in_file)
        in_file.close()
        print(f".london attribute has been loaded from {in_dir}")
        if not self.london._stations:
            print("Warning. No stations in loaded city")


class SimulationManager:
    def __init__(self, city: City, n_simulations: int):
        self.base_city = city
        self.n_simulations = n_simulations

    def run_simulations(self):
        print("Begin simulations -------------------")
        for i in range(self.n_simulations):
            city_instance = deepcopy(self.base_city)
            for t in range(60*24):
                # Each run simulates 24 hours, by minute
                _ = city_instance.main_elapse_time(1)
                if t % 60 == 0:
                    print(f"simulation: {i} \t hour: {t//60}")
        print(f"completed {self.n_simulations} simulations ")
        print("-------------------------------------")


