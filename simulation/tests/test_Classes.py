import pytest
from random import seed
from math import isclose
from ..sim_classes import City, Station, LondonCreator


# pytest fixtures define a class instance that can be re-used for various tests, by passing it as an argument
@pytest.fixture
def basic_city():
    """Basic city with two stations in it"""
    c = City()
    s = Station(16, 8, st_id=0)
    c.add_station(s)
    c.add_station(Station(16, 8, st_id=1))
    return c


@pytest.fixture
def nrly_empty_stn():
    """Station that has one bike left"""
    return Station(capacity=16, docked_init=1)


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
        assert len(basic_city._finished_journeys) == 1
        assert len(basic_city._failed_ends) == 0

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
        assert len(basic_city._finished_journeys) == 2
        assert len(basic_city._failed_ends) == 0

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
        assert len(basic_city._finished_journeys) == 1
        assert len(basic_city._failed_ends) == 1

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
        assert len(basic_city._finished_journeys) == 0
        assert len(basic_city._failed_ends) == 1
        # TODO: Actually handle and test new destination logic

    def test_failed_start(self, basic_city):
        basic_city.get_station(0)._docked = 0
        basic_city.generate_journey(
            start_st=basic_city.get_station(0)
            ,dest_st=basic_city.get_station(1)
            ,duration=3)
        assert len(basic_city._agents) == 0
        assert len(basic_city._finished_journeys) == 0
        assert len(basic_city._failed_ends) == 0
        assert len(basic_city._failed_starts) == 1

    def test_main_elapse_time(self, basic_city):
        """important test: includes a lot of simulation logic"""
        seed(16)
        basic_city.main_elapse_time(1)
        assert len(basic_city._agents) > 0
        basic_city.main_elapse_time(3)
        assert len(basic_city._finished_journeys) > 0
        assert basic_city._time == 4

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
        assert len(basic_city._failed_ends) == 1

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
        demand = trial_station.decide_journey_demand(1)
        assert len(demand) > 0


class TestLondonCreator:
    def test_populate_stations(self):
        lc = LondonCreator()
        lc.populate_tfl_stations()
        for station in lc.london._stations.values():
            assert 10 <= station._capacity <= 64
        assert lc.london.get_station(6)._capacity == 18
        assert isclose(lc.london.get_station(6)._latitude, 51.518117, abs_tol=0.000001)
        assert lc.london.get_station(6)._common_name.startswith('Broadcasting House')