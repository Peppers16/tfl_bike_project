from ..sim_classes import City, Station
import pytest


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
        basic_city.elapse_time(1)
        assert len(basic_city._agents) == 1
        assert basic_city._stations[0]._docked == 7
        assert basic_city._stations[1]._docked == 8
        basic_city.elapse_time(2)
        assert len(basic_city._agents) == 0
        assert basic_city._stations[0]._docked == 7
        assert basic_city._stations[1]._docked == 9

    def test_failed_end(self, basic_city):
        basic_city.get_station(1)._docked = 16
        basic_city.generate_journey(
            start_st=basic_city.get_station(0)
            ,dest_st=basic_city.get_station(1)
            ,duration=3)
        assert basic_city.get_station(0)._docked == 7
        assert basic_city.get_station(1)._docked == 16
        basic_city.elapse_time(3)
        assert basic_city.get_station(1)._docked == 16
        assert len(basic_city._agents) == 1
        # TODO: Actually handle this situation


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