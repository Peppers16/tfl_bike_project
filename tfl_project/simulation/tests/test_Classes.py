import pytest
from random import seed
from math import isclose
from tfl_project.simulation.sim_classes import City, Station
from tfl_project.simulation.sim_managment import LondonCreator, SimulationManager, IncompatibleParamsError
import os.path
from os import remove
from pathlib import Path
from numpy import nan

# A small version of London is pre-populated for some testing
test_london_location = 'simulation/tests/files/'
city_loc = Path(test_london_location) / 'london.pickle'
if city_loc.exists():
    remove(city_loc)
    remove(Path(test_london_location) / 'last_used_params.json')
if not city_loc.exists():
    import tfl_project.simulation.tests.pre_populate_test_london
    print(f"file not found: {test_london_location}. Executing script to create it...")
    tfl_project.simulation.tests.pre_populate_test_london.main()

# pytest fixtures define a class instance that can be re-used for various tests, by passing it as an argument
@pytest.fixture
def basic_city():
    """Basic city with two stations in it"""
    c = City()
    dummy_demand_dict = {0: 5}
    dummy_dest_dict = {0: {'destinations': [0, 1], 'volumes': [3, 7]}}
    dummy_duration_dict = {0: (6.12, 2.05), 1: (5.11, 1.85)}
    s = Station(16, 8, st_id=0, demand_dict=dummy_demand_dict, dest_dict=dummy_dest_dict, duration_dict=dummy_duration_dict)
    c.add_station(s)
    c.add_station(Station(16, 8, st_id=1, demand_dict=dummy_demand_dict, dest_dict=dummy_dest_dict, duration_dict=dummy_duration_dict))
    return c


@pytest.fixture
def nrly_empty_stn():
    """Station that has one bike left"""
    return Station(capacity=16, docked_init=1)


@pytest.fixture
def prepop_londoncreator():
    # additional SQL filters needed to pass compatibility check with output of pre_populate_test_london.py
    lc = LondonCreator(additional_sql_filters="""AND "StartStation Id" IN (1, 6, 14, 98, 393)
                AND "EndStation Id" IN (1, 6, 14, 98, 393)""")
    lc.load_pickled_city(test_london_location)
    return lc


class TestCity:
    def testcitystub(self, basic_city):
        assert isinstance(basic_city, City)
        assert len(basic_city._stations) == 2
        assert basic_city == basic_city._stations[0]._city

    def test_journey(self, basic_city):
        assert basic_city._stations[0]._docked == 8
        assert basic_city._stations[1]._docked == 8
        assert len(basic_city._agents) == 0
        basic_city.generate_journey(
            start_st=basic_city.get_station(0)
            ,dest_st=basic_city.get_station(1)
            ,duration=3)
        assert len(basic_city._agents) == 1
        assert basic_city._stations[0]._docked == 7
        assert basic_city._stations[1]._docked == 8
        basic_city.move_agents(1)
        assert len(basic_city._agents) == 1
        assert basic_city._stations[0]._docked == 7
        assert basic_city._stations[1]._docked == 8
        basic_city.move_agents(2)
        assert len(basic_city._agents) == 0
        assert basic_city._stations[0]._docked == 7
        assert basic_city._stations[1]._docked == 9
        assert basic_city._event_log['totals']['finished_journeys'] == 1
        assert basic_city._event_log['totals']['failed_ends'] == 0

    def test_two_journeys(self, basic_city):
        # two arriving at same time
        assert basic_city._stations[0]._docked == 8
        assert basic_city._stations[1]._docked == 8
        basic_city.generate_journey(
            start_st=basic_city.get_station(0)
            ,dest_st=basic_city.get_station(1)
            ,duration=1)
        basic_city.generate_journey(
            start_st=basic_city.get_station(0)
            ,dest_st=basic_city.get_station(1)
            ,duration=1)
        assert len(basic_city._agents) == 2
        basic_city.move_agents(1)
        assert basic_city.get_station(0)._docked == 6
        assert basic_city.get_station(1)._docked == 10
        assert len(basic_city._agents) == 0
        assert basic_city._event_log['totals']['finished_journeys'] == 2
        assert basic_city._event_log['totals']['failed_ends'] == 0

    def test_two_at_full(self, basic_city):
        basic_city.get_station(1)._docked = 15
        basic_city.generate_journey(
            start_st=basic_city.get_station(0)
            , dest_st=basic_city.get_station(1)
            , duration=1)
        basic_city.generate_journey(
            start_st=basic_city.get_station(0)
            , dest_st=basic_city.get_station(1)
            , duration=1)
        basic_city.move_agents(1)
        assert basic_city.get_station(1)._docked == 16
        assert len(basic_city._agents) == 1
        assert basic_city._event_log['totals']['finished_journeys'] == 1
        assert basic_city._event_log['totals']['failed_ends'] == 1

    def test_failed_end(self, basic_city):
        basic_city.get_station(1)._docked = 16
        basic_city.generate_journey(
            start_st=basic_city.get_station(0)
            ,dest_st=basic_city.get_station(1)
            ,duration=3)
        assert basic_city.get_station(0)._docked == 7
        assert basic_city.get_station(1)._docked == 16
        basic_city.move_agents(3)
        assert basic_city.get_station(1)._docked == 16
        assert len(basic_city._agents) == 1
        assert basic_city._event_log['totals']['finished_journeys'] == 0
        assert basic_city._event_log['totals']['failed_ends'] == 1

    def test_failed_start(self, basic_city):
        basic_city.get_station(0)._docked = 0
        basic_city.generate_journey(
            start_st=basic_city.get_station(0)
            ,dest_st=basic_city.get_station(1)
            ,duration=3)
        assert len(basic_city._agents) == 0
        assert basic_city._event_log['totals']['finished_journeys'] == 0
        assert basic_city._event_log['totals']['failed_ends'] == 0
        assert basic_city._event_log['totals']['failed_starts'] == 1

    def test_main_elapse_time(self, basic_city):
        """important test: includes a lot of simulation logic"""
        seed(16)
        basic_city.main_elapse_time(1)
        assert len(basic_city._agents) > 0
        basic_city.main_elapse_time(60)
        assert basic_city._event_log['totals']['finished_journeys'] > 0
        assert basic_city._time == 61

    def test_user_next_destination(self, basic_city):
        basic_city.get_station(1)._docked = 16
        basic_city.generate_journey(
            start_st=basic_city.get_station(0)
            , dest_st=basic_city.get_station(1)
            , duration=3)
        user = basic_city._agents[0]
        assert user._current_destination == basic_city.get_station(1)

        basic_city.move_agents(3)
        assert user.need_new_destination
        assert basic_city._event_log['totals']['failed_ends'] == 1

        basic_city.call_for_new_destinations()
        assert user._current_destination == basic_city.get_station(0)
        assert user._remaining_duration > 0
        assert not user.need_new_destination


class TestStation:
    def test_underflow(self, nrly_empty_stn):
        assert nrly_empty_stn._docked == 1
        nrly_empty_stn.give_bike()
        assert nrly_empty_stn._docked == 0
        with pytest.raises(Exception):
            nrly_empty_stn.give_bike()

    def test_overflow(self):
        s = Station(capacity=16, docked_init=15)
        s.take_bike()
        assert s._docked == 16
        with pytest.raises(Exception):
            s.take_bike()

    def test_bad_params(self):
        with pytest.raises(ValueError):
            Station(capacity=16, docked_init=17)
        with pytest.raises(ValueError):
            Station(capacity=-1, docked_init=0)
        with pytest.raises(ValueError):
            Station(capacity=0, docked_init=0)
        with pytest.raises(ValueError):
            Station(capacity=2, docked_init=-1)

    def test_generate_demand(self, basic_city):
        seed(16)
        trial_station = basic_city.get_station(0)
        demand = trial_station.decide_journey_demand(interval=0, elapsing=10)
        assert len(demand) > 0
        picked_destinations = [d[1] for d in demand]
        # the dummy distribution put station 1 as roughly twice as likely as station 0
        n_1_picked = picked_destinations.count(basic_city.get_station(1))
        n_0_picked = len(picked_destinations) - n_1_picked
        # assert that station 1 was picked more often
        assert 0 < n_0_picked < n_1_picked < len(picked_destinations)

    def test_distance_from(self, basic_city):
        # TODO
        pass


class TestLondonCreator:
    def test_populate_stations(self, prepop_londoncreator):
        for station in prepop_londoncreator.london._stations.values():
            assert 10 <= station._capacity <= 64
        assert prepop_londoncreator.london.get_station(6)._capacity == 18
        assert isclose(prepop_londoncreator.london.get_station(6)._latitude, 51.518117, abs_tol=0.000001)
        assert prepop_londoncreator.london.get_station(6)._common_name.startswith('Broadcasting House')

    def test_populate_station_demand_dicts(self, prepop_londoncreator):
        assert prepop_londoncreator.london.get_station(6)._demand_dict[0] > 0
        demand_at_midnight = prepop_londoncreator.london.get_station(6)._demand_dict[0]
        demand_at_8 = prepop_londoncreator.london.get_station(6)._demand_dict[480]
        assert demand_at_8 > demand_at_midnight
        kingsx_at_8 = prepop_londoncreator.london.get_station(14)._demand_dict[480]
        assert kingsx_at_8 > demand_at_8

    def test_populate_station_destination_dicts(self, prepop_londoncreator):
        i = prepop_londoncreator.london.get_station(98)._dest_dict[240]
        # at 8am, there were 192 journeys from station 98 to 393 in the standard 2015 period
        assert i['volumes'][i['destinations'].index(393)] == 192

    def test_elapse_time(self, prepop_londoncreator):
        seed(16)
        prepop_londoncreator.london.main_elapse_time(1)
        assert prepop_londoncreator.london._event_log['totals']['finished_journeys'] == 0
        for i in range(60*24):
            prepop_londoncreator.london.main_elapse_time(1)
        assert prepop_londoncreator.london._event_log['totals']['finished_journeys'] > 0

    def test_event_log(self, prepop_londoncreator):
        log = prepop_londoncreator.london._event_log
        seed(16)
        assert log['totals']['finished_journeys'] == 0
        for i in range(60*24):
            prepop_londoncreator.london.main_elapse_time(1)
        assert log['totals']['finished_journeys'] > 0
        assert log['totals']['finished_journeys'] == sum(log['time_series']['finished_journeys'])
        assert log['totals']['failed_starts'] == sum(log['time_series']['failed_starts'])
        assert log['totals']['failed_ends'] == sum(log['time_series']['failed_ends'])
        assert len([e for e in log['events']['event'] if e == 'finished_journeys']) == log['totals']['finished_journeys']
        assert len([e for e in log['events']['event'] if e == 'failed_starts']) == log['totals'][
            'failed_starts']
        assert len([e for e in log['events']['event'] if e == 'failed_ends']) == log['totals'][
            'failed_ends']

        df = prepop_londoncreator.london.get_timeseries_df()
        assert df.shape == (1440, 4)
        assert sum(df['finished_journeys']) == log['totals']['finished_journeys']
        df2 = prepop_londoncreator.london.get_events_df()
        assert len(df2) == len(log['events']['event'])

    def test_next_desination(self, prepop_londoncreator):
        london = prepop_londoncreator.london
        london.generate_journey(
            start_st=london.get_station(14)
            ,dest_st=london.get_station(98)
            ,duration=1)
        original_dest = london.get_station(98)
        original_dest._docked = original_dest._capacity
        london.main_elapse_time(1)
        new_dest = london._agents[0]._current_destination
        assert new_dest != original_dest
        for st in london._stations.values():
            if st != original_dest and st != new_dest:
                assert st.distance_from(original_dest) > new_dest.distance_from(original_dest)

    def test_next_destination_w_null(self, prepop_londoncreator):
        """Stations missing co-ordinates should not be selected as next destination"""
        london = prepop_londoncreator.london
        st_14 = london.get_station(14)
        st_14._latitude = None
        st_14._longitude = None
        london.generate_journey(
            start_st=london.get_station(1)
            ,dest_st=london.get_station(98)
            ,duration=1)
        london.get_station(98)._docked = london.get_station(98)._capacity
        london.main_elapse_time(1)
        new_dest = london._agents[0]._current_destination
        assert new_dest != st_14

    def test_next_destination_w_nan(self, prepop_londoncreator):
        """Stations missing co-ordinates should not be selected as next destination"""
        london = prepop_londoncreator.london
        st_14 = london.get_station(14)
        st_14._latitude = nan
        st_14._longitude = nan
        london.generate_journey(
            start_st=london.get_station(1)
            ,dest_st=london.get_station(98)
            ,duration=1)
        london.get_station(98)._docked = london.get_station(98)._capacity
        london.main_elapse_time(1)
        new_dest = london._agents[0]._current_destination
        assert new_dest != st_14


    def test_parameter_json(self, prepop_londoncreator):
        f_location = 'simulation/tests/files/last_used_params.json'
        assert os.path.exists(f_location)
        assert prepop_londoncreator.parameter_json_is_compatible(f_location)
        prepop_londoncreator.min_year = 2016
        assert not prepop_londoncreator.parameter_json_is_compatible(f_location)
        with pytest.raises(IncompatibleParamsError):
            prepop_londoncreator.load_pickled_city(test_london_location)
        with pytest.raises(IncompatibleParamsError):
            prepop_londoncreator.get_or_create_london(test_london_location)

    def test_duration_cache(self, prepop_londoncreator):
        path = Path('simulation/tests/files/caches/duration_params')
        assert (path / '393.json').exists()
        assert prepop_londoncreator.parameter_json_is_compatible(path / 'last_used_params.json')
        prepop_londoncreator.min_year = 2016
        with pytest.raises(NotImplementedError):
            prepop_londoncreator.populate_station_duration_params(path)
        d = prepop_londoncreator.london.get_station(393)._duration_dict
        assert 14 in d
        assert d[14] == (9.16312280185123, 1.632012029995245)


class TestSimulationManager:
    def test_simulations(self, prepop_londoncreator):
        sm = SimulationManager(
            city=prepop_londoncreator.london
            , n_simulations=2
            , simulation_id='TESTSIM'
        )
        sm.run_simulations()
        assert len(sm.combined_timeseries_df) == 2880
        assert 0 in sm.combined_timeseries_df['sim_num']
        assert 1 in sm.combined_timeseries_df['sim_num']
        assert len(sm.combined_event_df) > 0

    def test_output_to_csv(self, prepop_londoncreator):
        sm = SimulationManager(
            city=prepop_londoncreator.london
            , n_simulations=2
            , simulation_id='TESTSIM'
        )
        sm.run_simulations()
        sm.output_df_to_csv(sm.combined_timeseries_df, 'timeseries')
        test_dir = 'data/simulation_outputs/TESTSIM'
        assert os.path.exists(test_dir + '/timeseries.csv')
        os.remove(test_dir + '/timeseries.csv')
        sm.output_df_to_csv(sm.combined_event_df, 'events')
        assert os.path.exists(test_dir + '/events.csv')
        os.remove(test_dir + '/events.csv')
        os.rmdir(test_dir)
