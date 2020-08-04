from random import randint, choice, choices
import sqlite3
import numpy.random
from numpy import isnan
import pickle
from pandas import read_sql
from scipy.stats import gumbel_r
import time
from math import sqrt


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


class City:
    def __init__(self, interval_size=20):
        """
        The city class contains Agents and Stations, and has a time attribute.
        Whenever time elapses, User Agents (with destinations) may be generated at Stations.
        Stations must have a distinct st_id.

        The interval_size is a meta parameter that remembers the size of time interval that the station data is
        collected for. I.e. if interval = 20, then station demand will be grouped into 20-minute chunks.
        The simulation is not restricted to this interval.
        """
        self._stations = dict()
        self._agents = []
        self._time = 0
        self._interval_size = interval_size
        # It may make sense to create a class that logs data. For now, keeping simple with lists
        self._failed_starts = []
        self._failed_ends = []
        self._finished_journeys = []

    def move_agents(self, t):
        """Existing agents proceed with their journeys, potentially arriving at their destination.
        Agents handle their own .arrival() logic as part of travel()
        In simulation conditions this is called by main_elapse_time()"""
        for agent in self._agents:
            agent.travel(t)
        self.cleanup_agents()  # agents should not remove themselves whilst elapse_time is iterating over _agents

    def request_demand(self, interval, t):
        """City asks stations to decide what journeys will originate at them, and will attempt to generate any
        requested journeys.
        In simulation conditions this is called by main_elapse_time()
        :param interval: the current time interval that the simulation is in.
        :param t: the number of minutes that are elapsing during this 'round'
        """
        # Stations now generate demand for more journeys
        for station in self._stations.values():
            journey_demand = station.decide_journey_demand(interval=interval, elapsing=t)
            for j in journey_demand:
                self.generate_journey(*j)

    def call_for_new_destinations(self):
        """Simply instructs all agents to assign themselves a new destination if they need one"""
        for agent in self._agents:
            if agent.need_new_destination:
                agent.determine_next_destination()

    def main_elapse_time(self, t=1):
        """
        This is where the bulk of simulation behaviour takes place.
        The phases are:
            1. Existing agents travel(), during which they will handle their own arrival logic if they arrive at a dest.
                City cleans-up any agents who have flagged themselves as finished (i.e. arrived)
            2. Stations decide what journeys (if any) they will request. They return journey parameters and City
                will attempt to generate those journeys
            3. Agents in need of a new destination decide on their next destination

        This order was chosen to try and maximise the useful context available to objects when they perform their
        actions.
        """
        current_interval = (self._time // self._interval_size) * self._interval_size
        self.move_agents(t)
        self.request_demand(interval=current_interval, t=t)
        self.call_for_new_destinations()
        self._time += t

    def generate_journey(self, start_st, dest_st, duration:int):
        """
        Given:
            - A starting station
            - A destination station
            - A journey duration
        This method will attempt to generate a journey.

        If the starting station is empty, the journey will count as a failed start immediately. An Agent will
        not be instantiated in this case (as they could not even begin their journey).

        If the starting station is not empty, an Agent will be instantiated and undock a bike from the Station.

        Note: the 'demand' for journeys is generated by the stations themselves: the stations ask City
        to generate journeys on their behalf. As part of City.request_demand()
        :return:
        """
        if start_st.is_empty():
            self.log_failed_start()
        else:
            u = User(self, dest_st, duration)
            self._agents.append(u)
            u.undock_bike(start_st)

    def cleanup_agents(self):
        """remove agents from the city if they are finished"""
        self._agents = [a for a in self._agents if not a.finished]

    def add_station(self, s):
        """
        Assigns a station object to the city by adding it to City._stations. This simultaneously adds the city as
        the station's ._city attribute.
        :param s:
        :return:
        """
        key = s.get_id()

        if key in self._stations:
            raise ValueError(f"Station with ID {key} is already in city")

        self._stations[key] = s
        s._city = self

    def get_station(self, key):
        return self._stations[key]

    def log_failed_end(self):
        self._failed_ends.append(self._time)

    def log_failed_start(self):
        self._failed_starts.append(self._time)

    def log_finished_journey(self):
        self._finished_journeys.append(self._time)


class Station:
    def __init__(self, capacity=None, docked_init=None, st_id=None, demand_dict=None, dest_dict=None, duration_dict=None):
        """
        A Station that can receive or release bikes, e.g. bikepoint or depot.
        capacity: total number of docks.
        docked_init: number of bikes docked when Station is instantiated
        st_id: an identifier that will be used to locate the Station when it is added to a City object

        :param capacity: int
        :param docked_init: int
        :param st_id: int
        """
        if capacity < 1:
            raise ValueError(f"Capacity must be at least 1. {capacity} was given")
        if docked_init < 0 or docked_init > capacity:
            raise ValueError(f"docked_init must be between 0 and capacity. {docked_init} was given")

        self._capacity = capacity
        self._docked = docked_init
        self._id = st_id
        self._city = None
        self._latitude = 0
        self._longitude = 0
        # Journey demand simulation parameters
        if demand_dict:
            self._demand_dict = demand_dict
        else:
            self._demand_dict = dict()

        if dest_dict:
            self._dest_dict = dest_dict
        else:
            self._dest_dict = {}

        if duration_dict:
            self._duration_dict = duration_dict
        else:
            self._duration_dict = {}

    def is_empty(self):
        return self._docked == 0

    def is_full(self):
        return self._docked == self._capacity

    def give_bike(self):
        """If the station is not empty, undocks a bike and returns true"""
        if not self.is_empty():
            self._docked -= 1
            return True
        else:
            raise Exception('Bike underflow occurred')

    def take_bike(self):
        """If the station is not full, docks a bike and returns false"""
        if not self.is_full():
            self._docked += 1
            return True
        else:
            raise Exception('Bike overflow occurred')

    def get_id(self):
        return self._id

    def decide_journey_demand(self, interval, elapsing=1):
        """
        The station will decide what journeys will start at it during the elapsing time period, including destinations
        and durations, and return their parameters.

        It returns a list of (self, dest_st, duration) tuples.
        """
        # TODO: Replace Dummy logic with realistic demand. Right now station picks random destination, possibly itself
        journey_demand = []
        # check station's demand per minute during this time interval (e.g. 20-40th minute)
        if interval in self._demand_dict:
            demand_p_min = self._demand_dict[interval]
        else:
            demand_p_min = 0
        # number of journeys is sampled from poisson process based on current demand per minute
        n_journeys = numpy.random.poisson(lam=demand_p_min*elapsing)

        for i in range(n_journeys):
            if interval in self._dest_dict:
                # destinations sampled from multinomial distribution based on previous destinations at this interval
                dest_id = choices(
                    population=self._dest_dict[interval]['destinations']
                    , weights=self._dest_dict[interval]['volumes']
                    , k=1
                )[0]
                destination = self._city.get_station(dest_id)
            else:
                print(f"Warning: Station {self._id} was asked to generate unprecedented demand for interval {interval}")
                destination = choice(list(self._city._stations.values()))
                dest_id = destination.get_id()
            # decide duration using gumbel_r distribution
            if dest_id in self._duration_dict:
                duration = round(gumbel_r(*self._duration_dict[dest_id]).rvs(1)[0])
            else:
                print(f"Warning: Station {self._id} was asked to generate unprecedented duration for destination {dest_id}")
                duration = round(gumbel_r(*choice(self._duration_dict.values())).rvs(1)[0])
            journey_demand.append((self, destination, duration))
        return journey_demand

    def add_dest_volume_parameter(self, interval, destination_id, journeys):
        if interval not in self._dest_dict:
            self._dest_dict[interval] = {'destinations': [], 'volumes': []}
        interval_entry = self._dest_dict[interval]
        interval_entry['destinations'].append(destination_id)
        interval_entry['volumes'].append(journeys)

    def add_dest_duration_params(self, destination_id, params):
        self._duration_dict[destination_id] = params

    def distance_from(self, other):
        """Give distance of self from other based on co-ordinates
        Technically, Euclidean distance is not a perfect measure of distance between co-ordinates due to projection
        of Earth's surface. But this inaccuracy can be ignored since we are just finding closest stations within a
        relatively tiny area"""
        dist = sqrt((self._latitude - other._latitude)**2 + (self._longitude - other._longitude)**2)
        return dist


class Agent:
    def __init__(self, city: City, destination: Station, duration: int):
        """This is the parent class / interface for Users and Trucks"""
        self._current_destination = destination
        self._remaining_duration = duration
        self._city = city
        self.finished = False
        self.need_new_destination = False

    def dock_bike(self):
        pass

    def undock_bike(self, station:Station):
        pass

    def determine_next_destination(self):
        candidates = [st for st in self._city._stations.values() if not st.is_full()]
        candidates.sort(
            key=lambda x: x.distance_from(self._current_destination)
        )
        new_destination = candidates[0]
        # TODO: There is a small risk of asking for an unprecedented duration here
        new_duration = round(gumbel_r(*self._current_destination._duration_dict[new_destination.get_id()]).rvs(1)[0])
        self._current_destination = new_destination
        self._remaining_duration = new_duration
        self.need_new_destination = False

    def arrival(self):
        pass

    def travel(self, t):
        """Reduces remaining duration and calls Agent.arrival() if user has arrived"""
        self._remaining_duration -= t
        if self._remaining_duration < 0.5:  # TODO: check you are happy with this condition
            self.arrival()


class User(Agent):
    def arrival(self):
        """Overrides arrival with User behaviour"""
        if self._current_destination.is_full():
            self._city.log_failed_end()
            self.need_new_destination = True
        else:
            self.dock_bike()

    def dock_bike(self):
        """A user is removed after docking a bike sucessfully"""
        self._current_destination.take_bike()
        self.finished = True
        self._city.log_finished_journey()

    def undock_bike(self, station: Station):
        station.give_bike()