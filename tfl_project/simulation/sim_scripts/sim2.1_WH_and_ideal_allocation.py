from tfl_project.simulation.sim_managment import LondonCreator, SimulationManager
from tfl_project.simulation.city import City
from tfl_project.simulation.station import WarehousedStation
from pathlib import Path
from pandas import read_csv
from tfl_project.simulation.sim_scripts.describe_city import describe_city

ideals_loc = Path('data/analytical_outputs/reu/bikepoint_reu_inferences.csv')


def modify_city_from_csv(city: City, csv_loc: Path, station_col: str, cap_col: str, bike_col: str):
    """This function reads a CSV of preferred capacities and bike allocations and modifies stations in the city to
    have those allocations.
    - Will only increase capacity: does not reduce capacity.
    - Skips WarehousedStations: their capacity is already catered-for by the warehouse!

    This implementation violates encapsulation and would ideally be a class method: refactor if time permits."""
    df = read_csv(csv_loc, usecols=[station_col, cap_col, bike_col])
    for _, ideal in df.iterrows():
        assert ideal[cap_col] >= ideal[bike_col]
        st = city.get_station(ideal[station_col])
        if isinstance(st, WarehousedStation):  # do not modify capacity for warehoused stations: overstated
            continue
        if ideal[cap_col] > st._capacity:
            st._capacity = ideal[cap_col]
        st._docked = ideal[bike_col]
        assert st._capacity >= st._docked


def main():
    """
    Using conservative warehouse capacities as suggested by the REU profiles.
    AND using the conservative station capacities suggested by REU profiles.
    :return:
    """
    warehouse_params = [
        {'capacity': 520, 'docked_init': 520, 'st_id': 'WATERLOO'}
        , {'capacity': 220, 'docked_init': 220, 'st_id': 'KINGSX'}
        , {'capacity': 150, 'docked_init': 0, 'st_id': 'HOLBORN'}
    ]

    warehoused_stations = {
        # Waterloo Stations 1, 2, 3
        374: 'WATERLOO',
        361: 'WATERLOO',
        154: 'WATERLOO',
        # Belgrove Street, King's Cross
        14: 'KINGSX',
        # Holborn Circus, New Fetter, Stonecutter
        66: 'HOLBORN',
        546: 'HOLBORN',
        112: 'HOLBORN',
    }

    base_london = LondonCreator(
            min_year=2015
            , minute_interval=20
            , exclude_covid=True
            , warehouse_param_list=warehouse_params
            , warehoused_stations=warehoused_stations) \
        .get_or_create_london(pickle_loc='simulation/files/pickled_cities/london_big_warehouses')

    # Amend station capacities to the (counter-factual) ideals dervied in Demand Profiles MSP-6
    modify_city_from_csv(base_london, ideals_loc, 'station', 'conservative capacity needed', 'conservative bikes needed')

    describe_city(base_london)

    sm = SimulationManager(city=base_london, n_simulations=20, simulation_id='SIM_WH_CONSERV_ALLOC')
    sm.run_simulations()
    sm.output_dfs_to_csv()


if __name__ == '__main__':
    main()
