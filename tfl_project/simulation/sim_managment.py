import pickle
import sqlite3
import time
from copy import deepcopy
from pandas import read_sql
from scipy.stats import gumbel_r
from pandas import DataFrame
import json
from pathlib import Path

from tfl_project.simulation.city import City
from tfl_project.simulation.station import Station, Store, WarehousedStation


class IncompatibleParamsError(Exception):
    pass


class LondonCreator:
    def __init__(self, min_year=2015, minute_interval=20, exclude_covid=True
                 , additional_sql_filters="""""", warehouse_param_list=None, warehoused_stations: dict = None):
        """
        Creates a city that emulates the true London BBS, including its stations.

        min_year: First year from which simulation data will be modelled
        minute_interval: The granularity with which data will be summarised. E.g. if 20, the journey demand per
            station will be calculated per every 20-minute interval in a 24 hour period.
        warehouse_list: A list of tuples giving Store parameters which should be added to the city to serve as warehouses.
        warehoused_stations: A dictionary of bikepoint ids mapping to warehouse IDs. These bikepoints are coupled to
            those warehouses and can freely exchange bikes with them.
        """
        self.london = City(interval_size=minute_interval)
        self.min_year = min_year
        self.minute_interval = minute_interval
        self.additional_filters = additional_sql_filters
        self.warehouse_param_list = warehouse_param_list
        self.warehoused_stations = warehoused_stations
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

    def populate_warehouses(self):
        if self.warehouse_param_list:
            for wt in self.warehouse_param_list:
                warehouse = Store(**wt)
                self.london.add_warehouse(warehouse)

    def populate_tfl_stations(self):
        """
        Takes the new city and adds stations to it which reflect the true TFL BSS. Uses a SQLite table,
        station_metadata, which has already been prepared. The initial number of docked bikes is set to a default
        value equal to the mean 5-am number observed in the station_fill data pre-covid
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
                ,IFNULL(avg_5am_docked, 0)
            FROM station_metadata
            WHERE bikepoint_id > 0 
            """
        )
        print("Populating stations")
        for row in rows:
            st_id = row[0]
            if self.warehoused_stations and st_id in self.warehoused_stations:
                # The station needs to get instantiated as a WarehousedStation
                wh = self.london.get_warehouse(self.warehoused_stations[st_id])
                s = WarehousedStation(capacity=row[1]
                                      , docked_init=row[5]
                                      , st_id=st_id
                                      , latitude=row[3]
                                      , longitude=row[4]
                                      , warehouse=wh
                                      )
            else:
                s = Station(capacity=row[1]
                            , docked_init=row[5]
                            , st_id=st_id
                            , latitude=row[3]
                            , longitude=row[4]
                            )
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
                    AND weekday_ind = 1
                    AND "StartStation Id" != -1
                    AND "StartStation Id" NOT NULL
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
                AND weekday_ind = 1
                AND "StartStation Id" != 0
                AND "StartStation Id" NOT NULL
                AND "EndStation Id" != 0
                AND "EndStation Id" NOT NULL
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

    def get_params_from_cache(self, station_id, cache_loc):
        compatibility_json_loc = cache_loc / 'last_used_params.json'
        st_params_loc = cache_loc / (str(station_id) + '.json')
        if not self.parameter_json_is_compatible(compatibility_json_loc):
            raise IncompatibleParamsError("Cached duration parameters made by incompatible LondonCreator instance.")
        with open(st_params_loc) as infile:
            d = json.load(infile)
        # cast back into original format: json gets this a bit wrong
        d = {int(k): tuple(v) for k, v in d.items()}
        return d

    def cache_station_params(self, station_id, dictionary, cache_loc):
        json_file = str(station_id) + '.json'
        self.check_prepare_cache(cache_loc)
        # cast keys to vanilla python integer type, as opposed to numpy.int64
        dictionary = {int(k): v for k, v in dictionary.items()}
        with open(Path(cache_loc) / json_file, 'w') as f:
            json.dump(dictionary, f)

    def check_prepare_cache(self, cache_loc: Path):
        """Checks the cache location either has:
            - A compatible last_used_params.json
            - or, no last_used_params.json, in which case it adds one."""
        compatibility_json_loc = cache_loc / 'last_used_params.json'
        if compatibility_json_loc.exists():
            if not self.parameter_json_is_compatible(compatibility_json_loc):
                raise IncompatibleParamsError("Tried to cache to a location with pre-existing parameters that are "
                                              "incompatible")
            else:
                return
        else:
            # no compatibility_json present: write our own
            self.dump_parameter_json(compatibility_json_loc)

    def fetch_duration_params(self, start_id):
        d = dict()
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
                AND weekday_ind = 1
                -- Query plan more efficient if we specify these rather than ESid > 0
                AND "EndStation Id" != -1
                AND "EndStation Id" NOT NULL
                {self.additional_filters}
            """
        )
        print(f"fetched {len(journey_df)} journeys for station {start_id} in {(time.time()-start_time)} seconds")
        start_time = time.time()
        journey_df.dropna(subset=['Duration'], inplace=True)
        for end_id in journey_df["EndStation Id"].unique():
            durations = journey_df.loc[journey_df["EndStation Id"] == end_id]['Duration'].values
            # creates a tuple of scipy.stats.gumbel_r parameters
            params = gumbel_r.fit(durations)
            d[end_id] = params
        print(f"\tfitted {len(journey_df)} journeys in {(time.time()-start_time)/60} minutes")
        return d

    def populate_station_duration_params(self, cache_loc=Path('simulation/files/caches/duration_params')):
        """This is the most intensive parametrization, taking about 2 hours.
        Therefore, this method uses a 'cache' in addition to the existing .pickle_city functionality.
        This means we can create new LondonCreator instances (e.g. after updating source code) more flexibly without
        doing this step from scratch every time."""
        # This is intensive so populates one origin station at a time
        for start_id in self.london._stations.keys():
            try:
                d = self.get_params_from_cache(start_id, cache_loc)
            except FileNotFoundError:
                d = self.fetch_duration_params(start_id)
                self.cache_station_params(start_id, d, cache_loc)
            except IncompatibleParamsError:
                raise NotImplementedError("I need to decide how to handle this situation if it ever arises")
            # add the distribution parameters to the duration dict
            for end_id, params in d.items():
                self.london.get_station(start_id).add_dest_duration_params(destination_id=end_id, params=params)

    def create_london_from_scratch(self):
        print("Creating City using fresh data pulls")
        self.populate_warehouses()
        self.populate_tfl_stations()
        self.populate_station_demand_dicts()
        self.populate_station_destination_dicts()
        self.populate_station_duration_params()
        print("Done!")
        print(".london attribute has been populated using fresh SQL pulls")

    def pickle_city(self, out_dir='simulation/files/pickled_cities/london/'):
        """Pickles the city to the specified directory, and also saved a parameter json for future
        compatibility checks"""
        city_loc = Path(out_dir) / 'london.pickle'
        json_loc = Path(out_dir) / 'last_used_params.json'

        with open(city_loc, 'wb') as f:
            pickle.dump(self.london, f)
        self.dump_parameter_json(json_loc)
        print(f'City saved as {city_loc} for future use. Use load_pickled_city to use it again')

    def load_pickled_city(self, in_dir='simulation/files/pickled_cities/london/'):
        city_loc = Path(in_dir) / 'london.pickle'
        json_loc = Path(in_dir) / 'last_used_params.json'

        # This is a quick guard-rail against loading a pickled city when you have asked for non-default values
        if not self.parameter_json_is_compatible(json_loc):
            raise IncompatibleParamsError(f"{json_loc} indicates that {city_loc} has incompatible parameters")
        with open(city_loc, 'rb') as f:
            self.london = pickle.load(f)
        print(f".london attribute has been loaded from {in_dir}")
        if not self.london._stations:
            print("Warning. No stations in loaded city")

    def get_or_create_london(self, pickle_loc='simulation/files/pickled_cities/london'):
        try:
            self.load_pickled_city(in_dir=pickle_loc)
        except FileNotFoundError:
            print('existing pickled London not found: creating from scratch.')
            self.create_london_from_scratch()
            self.pickle_city(out_dir=pickle_loc)
        except IncompatibleParamsError:
            error_string = 'Previously pickled city is incompatible with your current LondonCreator parameters.\n' \
                    'Pass the location of either: a blank directory, or the location of a compatible pickled city.'
            print(error_string)
            raise
        return self.london

    def dump_parameter_json(self, out_f='simulation/files/last_used_params.json'):
        """This saves the current LondonCreator parameters to a JSON so that cached simulation parameters can be
        checked for 'compatibility' with future LondonCreator instances"""
        d = vars(self).copy()  # careful not to delete the actual london attribute from self!
        del d['london']
        with open(Path(out_f), 'w') as outfile:
            json.dump(d, outfile)

    def parameter_json_is_compatible(self, in_f):
        """Checks attributes of this LondonCreator against a previously-saved parameter json and returns true if it
        has matching attributes.

        Note: The check will pass if the previously saved json lacks attributes which have since been added to LondonCreator.
        This should ideally be dealt with, but for now I am content with this because it means that the 'base london'
        cached duration parameters can also be used by 'warehoused london'"""
        with open(Path(in_f)) as infile:
            d = json.load(infile)
        for k, v in d.items():
            # This block looks a bit messy now and stems from the fact that json converts integer dict keys to strings.
            # After adding the LondonCreator.warehoused_stations attribute I had to do this workaround.
            # Would be nice to find a neater workaround if possible.
            if k == 'warehoused_stations':  # has to be assessed differently because json saves keys as strings
                if v is None:
                    if self.warehoused_stations is not None:
                        return False
                else:
                    for st_id, wh in v.items():
                        try:
                            if self.warehoused_stations[int(st_id)] != wh:
                                return False
                        except KeyError:
                            return False
            elif self.__dict__[k] != v:
                return False
        return True


class SimulationManager:
    def __init__(self, city: City, n_simulations: int, simulation_id: str):
        """
        :param city: Pass a City instance which will undergo 24 simulation-hours, n times
        :param n_simulations: Number of times to repeat the simulation.
        :param simulation_id: A string which should uniquely identify this set of simulations.
            The CSVs resulting from the simulation will be stored in tfl_project/data/simulation_outputs/<simulation_id>
        """
        self.base_city = city
        self.n_simulations = n_simulations
        self.simulation_id = simulation_id
        self.combined_timeseries_df = None
        self.combined_event_df = None

    def run_simulations(self):
        print("Begin simulations -------------------")
        for i in range(self.n_simulations):
            print(f"Simulation {i} -----------")
            city_instance = deepcopy(self.base_city)
            for t in range(60*24):
                # Each run simulates 24 hours, by minute
                city_instance.main_elapse_time(1)
                if t % 60 == 0:
                    print(f"simulation: {i} \t hour: {t//60}")
            # This feels clunky...
            self.combined_timeseries_df = self.append_to_combined_df(self.combined_timeseries_df, self.simulation_id, i, city_instance.get_timeseries_df())
            self.combined_event_df = self.append_to_combined_df(self.combined_event_df, self.simulation_id, i, city_instance.get_events_df())
        print(f"completed {self.n_simulations} simulations ")
        print("-------------------------------------")

    def append_to_combined_df(self, combined_df: DataFrame, simulation_id: str, sim_num: int, instance_df: DataFrame):
        instance_df['simulation_id'] = simulation_id
        instance_df['sim_num'] = sim_num
        if combined_df is None:
            combined_df = instance_df
        else:
            combined_df = combined_df.append(instance_df.copy(), ignore_index=True)
        return combined_df

    def output_df_to_csv(self, df, descriptor=''):
        output_dir = Path('data/simulation_outputs/') / self.simulation_id
        if not output_dir.exists():
            output_dir.mkdir()
        output_file = output_dir / (descriptor + '.csv')
        if output_file.exists():
            print(output_file, 'already exists. Over-writing...')
            output_file.unlink()
        df.to_csv(output_file, index=False)

    def output_dfs_to_csv(self):
        self.output_df_to_csv(self.combined_timeseries_df, 'time_series')
        self.output_df_to_csv(self.combined_event_df, 'events')
