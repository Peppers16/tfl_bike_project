from tfl_project.simulation.sim_managment import LondonCreator, SimulationManager


def main():
    base_london = LondonCreator(min_year=2015, minute_interval=20, exclude_covid=True)\
        .get_or_create_london(pickle_loc='simulation/files/pickled_cities/london')
    sm = SimulationManager(city=base_london, n_simulations=20, simulation_id='SIM_BASE_5AM_NO_REBAL')
    sm.run_simulations()
    sm.output_dfs_to_csv()


if __name__ == '__main__':
    main()
