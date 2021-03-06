from tfl_project.simulation.sim_managment import LondonCreator, SimulationManager
from tfl_project.simulation.scenario_scripts.describe_city import describe_city


def main():
    base_london = LondonCreator(min_year=2015, minute_interval=20, exclude_covid=True)\
        .get_or_create_london(pickle_loc='tfl_project/simulation/files/pickled_cities/london')
    describe_city(base_london)
    sm = SimulationManager(city=base_london, n_simulations=20, simulation_id='SIM0_BASE_5AM_NO_REBAL')
    sm.run_simulations()
    sm.output_dfs_to_csv()


if __name__ == '__main__':
    main()
