from math import sqrt
from random import choices, choice

import numpy.random
from numpy import nan
from scipy.stats import gumbel_r


class BikeUnderflowException(Exception):
    pass


class BikeOverflowException(Exception):
    pass


class Store:
    def __init__(self, capacity: int, docked_init: int, st_id=None, latitude=0, longitude=0):
        """A Store is a parent class which could be a station or a warehouse. It contains bikes and can receive or
        release them. It has a finite capacity.
        capacity: total number of storage.
        docked_init: number of bikes stored when Store is instantiated
        """
        if capacity < 1:
            raise ValueError(f"Capacity must be at least 1. {capacity} was given")
        if docked_init < 0 or docked_init > capacity:
            raise ValueError(f"docked_init must be between 0 and capacity. {docked_init} was given")

        self._docked = docked_init
        self._latitude = latitude
        self._city = None
        self._capacity = capacity
        self._longitude = longitude
        self._id = st_id

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
            raise BikeUnderflowException('Bike underflow occurred')

    def take_bike(self):
        """If the store is not full, docks a bike and returns True"""
        if not self.is_full():
            self._docked += 1
            return True
        else:
            raise BikeOverflowException('Bike overflow occurred')

    def distance_from(self, other):
        """Give distance of self from other based on co-ordinates
        Technically, Euclidean distance is not a perfect measure of distance between co-ordinates due to projection
        of Earth's surface. But this inaccuracy can be ignored since we are just finding closest stations within a
        relatively tiny area"""
        try:
            dist = sqrt((self._latitude - other._latitude)**2 + (self._longitude - other._longitude)**2)
        except TypeError:
            dist = nan
        return dist

    def get_id(self):
        return self._id


class Station(Store):
    def __init__(self, capacity, docked_init, st_id=None, demand_dict=None, dest_dict=None, duration_dict=None,
                 latitude=0, longitude=0):
        """
        A Station is used directly by agents who begin and end journeys at stations.
        A station has various attributes relating to demand at a given time interval, and can be asked by City to
        decide on its own journey demand at a point in time.

        st_id: an identifier that will be used to locate the Station when it is added to a City object

        :param capacity: int
        :param docked_init: int
        :param st_id: int
        """
        super().__init__(capacity=capacity, docked_init=docked_init, st_id=st_id, latitude=latitude, longitude=longitude)

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

    def decide_journey_demand(self, interval, elapsing=1):
        """
        The station will decide what journeys will start at it during the elapsing time period, including destinations
        and durations, and return their parameters.

        It returns a list of (self, dest_st, duration) tuples.
        """
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
            duration = self.pick_duration(dest_id)
            journey_demand.append((self, destination, duration))
        return journey_demand

    def pick_duration(self, dest_id):
        """Randomly pick a duration based on the gumbel_r distribution for durations from self to destination station.
        If an unprecendented destination is selected, a random gumbel is picked from self"""
        if dest_id in self._duration_dict:
            duration = round(gumbel_r(*self._duration_dict[dest_id]).rvs(1)[0])
        else:
            print(f"Warning: Station {self._id} was asked to generate unprecedented duration for destination {dest_id}")
            duration = round(gumbel_r(*choice(list(self._duration_dict.values()))).rvs(1)[0])
        duration = max(duration, 1)
        return int(duration)

    def add_dest_volume_parameter(self, interval, destination_id, journeys):
        if interval not in self._dest_dict:
            self._dest_dict[interval] = {'destinations': [], 'volumes': []}
        interval_entry = self._dest_dict[interval]
        interval_entry['destinations'].append(destination_id)
        interval_entry['volumes'].append(journeys)

    def add_dest_duration_params(self, destination_id, params):
        self._duration_dict[destination_id] = params


class WarehousedStation(Station):
    """A Station that is directly linked to a (shared) Store.
    If the WarehousedStation becomes full or empty it will give or take a bike from the Store for free.
    The operation takes no time: the assumption is in real life storage and retrieval happens preemptively.

    It is up to the programmer to assign a realistic warehouse. The location of the warehouse won't be checked.
    """
    def __init__(self, capacity: int, docked_init: int, warehouse: Store,
                 st_id=None, demand_dict=None, dest_dict=None, duration_dict=None, latitude=0, longitude=0):
        super().__init__(capacity, docked_init, st_id, demand_dict, dest_dict, duration_dict, latitude, longitude)
        self._warehouse = warehouse

    def try_bike_from_warehouse(self):
        try:
            self._warehouse.give_bike()
            self._docked += 1
        except BikeUnderflowException:
            return

    def try_bike_to_warehouse(self):
        try:
            self._warehouse.take_bike()
            self._docked -= 1
        except BikeOverflowException:
            return

    def give_bike(self):
        """The WarehousedStation will try to avoid being empty if possible"""
        if self._docked == 1:
            self.try_bike_from_warehouse()
        super().give_bike()

    def take_bike(self):
        """The WarehousedStation will try to avoid being full if possible"""
        if self._docked == (self._capacity - 1):
            self.try_bike_to_warehouse()
        super().take_bike()
