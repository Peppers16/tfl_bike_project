from tfl_project.database_creation import make_SQLite_DB, station_data_to_sql, station_meta_to_sql

# This currently assumes you'll run script directly with tfl_project as the working directory
# May be subject to change if we wrap this in yet another script
if __name__ == '__main__':
    print("Creating database and indexed journeys table (will take a while)")
    make_SQLite_DB.main()
    print("Uploading station status data from csvs")
    station_data_to_sql.main()
    print("Creating a station_metadata table")
    station_meta_to_sql.main()
    print("Database creation complete.")