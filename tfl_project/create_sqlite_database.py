from tfl_project.database_creation import bp_lookups_from_tfl, journey_data_to_sql, station_data_to_sql, station_meta_to_sql
from tfl_project.cycle_journey_prep import clean_combined_cycle_data

# This currently assumes you'll run script directly with tfl_project as the working directory
# May be subject to change if we wrap this in yet another script
if __name__ == '__main__':
    print("Fetching TFL bikepoint lookups if necessary")
    bp_lookups_from_tfl.main()
    print("Uploading station status data from csvs")
    station_data_to_sql.main()
    print("Creating a station_metadata table")
    station_meta_to_sql.main()
    print("Adding column for typical 5am bike allocation")
    station_meta_to_sql.add_avg_5am_docked(pre_covid=True)
    print("Cleansing combined csv journey data if needed (slow)")
    clean_combined_cycle_data.main()
    print("Creating indexed journeys table (will take a while)")
    journey_data_to_sql.main()
    print("Database creation complete.")
