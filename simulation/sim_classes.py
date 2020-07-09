class City:
    def __init__(self):
        """
        The city class contains Agents and Stations, and has a time attribute.
        Whenever time elapses, User Agents (with destinations) may be generated at Stations.
        Stations must have a distinct st_id.
        """
        self._stations = dict()
        self._agents = []
        self._time = 0
        # It may make sense to create a class that logs data. For now, keeping simple with lists
        self._failed_starts = []
        self._failed_ends = []
        self._finished_journeys = []

    def elapse_time(self, t=1):
        """After being created, this is where the bulk of agent actions take place"""
        self._time += t
        # TODO: eventually make this more efficient so it does not have to pass _agents 3 times
        for agent in self._agents:
            agent.travel(t)
        self.cleanup_agents()  # agents should not remove themselves whilst elapse_time is iterating over _agents
        for agent in self._agents:  # agents should determine next destination when others are done travelling
            if agent.need_new_destination:
                agent.determine_next_destination()

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
    def __init__(self, capacity=None, docked_init=None, st_id=None):
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
        # TODO: ASSIGN NEW STATION TO self._current_destination
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