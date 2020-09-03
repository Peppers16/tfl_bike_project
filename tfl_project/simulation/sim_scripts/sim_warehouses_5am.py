from tfl_project.simulation.sim_managment import LondonCreator, SimulationManager
from tfl_project.simulation.sim_scripts.describe_city import describe_city

def main():
    """Using rounded warehouse capacities: These were just ballpark estimates which could be refined. """
    warehouse_params = [
        {'capacity': 300, 'docked_init': 300, 'st_id': 'WATERLOO'}
        , {'capacity': 200, 'docked_init': 200, 'st_id': 'KINGSX'}
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
        .get_or_create_london(pickle_loc='simulation/files/pickled_cities/london_warehouses')
    describe_city(base_london)
    sm = SimulationManager(city=base_london, n_simulations=20, simulation_id='SIM_WAREHOUSE_5AM_NO_REBAL')
    sm.run_simulations()
    sm.output_dfs_to_csv()


if __name__ == '__main__':
    main()
