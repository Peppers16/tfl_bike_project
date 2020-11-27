# TfL BSS Project

Welcome to my MSc project!

## If you are here for a showcase of my work
* For **Data Science**, visualisations and SQL, please browse the notebooks
* For **Software Engineering** and **Object Oriented Programming** in Python, please browse `tfl_project/simulation`
* For data logging via an API please see `tfl_project/tfl_api_logger`
* For some basic **Data Engineering** please see `tfl_project/database_creation` 
* For **data cleansing** please see `tfl_project/cycle_journey_prep`

## Understanding this repository

This readme is intended to give an orientation around the repository, but for full context it is advisable to read the 
accompanying report.  

Please note: Large files, including data, have _not_ been committed to the repository. Therefore many scripts won't 
simply run 'out of the box' as it is prerequisite that certain data and files have been prepared.

You will be able to run some scripts (see 'getting started' section), but unfortunately you will not be able to make 
full use of the repo if you simply clone it, as some of the data (e.g. station data) will be unavailable to you. 

## Overview of Key Sections
This is a multipurpose repository containing various sub-packages. Broadly there are four sections, some of which have 
their own dedicated readme file with more details. The following list is roughly in order of 'dependence' with earlier 
items being needed by latter items. 

*  _tfl_api_logger_: largely devoted to scripts which make API calls and log data to CSV. The most important one is 
probably `bikeStationStatus.py`, for gathering **station data**, which was scheduled to periodically execute on a 
Raspberry Pi device. 
* _cycle_journey_prep_: scripts for downloading, combining and cleaning TfL's open **journey data**.
* _database_creation_: Used by `tfl_project/create_sqlite_database.py` and containing various scripts which, if 
prerequisite CSVs are ready, create a SQLite database and performs many steps to 'extract, transform and load' data into 
a proper database schema. The key output is: `tfl_project/data/bike_db.db`.
Unfortunately, you'll need to ask me for a copy of the station data for this to work.
* _simulation_: All modules and scripts related to running simulations of the BSS. 

There is also a _Notebooks_ directory for exploration and analysis.  
 
## Getting Started
### Working directory
Project code is intended to be run from the **repository root**. 

Make sure your IDE, interpreter or terminal are set to use the respository root as the working directory (including when running scripts)
, or you may encounter issues with relative references and imports.  
##### A note on running scripts directly from the terminal:
There are a handful of scripts which, if run directly from the terminal or cmd, may result in 'module not found' errors. 
The reason for this is because running something like ```python foo/bar/some_script.py``` in the terminal does not 
automatically mean that the terminal working directory is added to the Python interpreter's path, so imports beginning 
with `foo.` can fail.

The solution to this is: either use an IDE which automatically appends the CWD to the python `sys.path`, or run the script 
as a module. The examples below assume that you are running them in the CMD, so you shouldn't have any problems.  

### Conda environment
Use Conda to create a virtual environment with the libraries that were used in development. If you are using windows you 
can exactly recreate my environment using:

```conda env create -f windows_environment.yml```

Alternatively a cross-platform file can be used: ```conda env create -f environment.yml```

### Fetching Journey Data
This is very slow (~5GB), but you can try running: 

```python tfl_project/cycle_journey_prep/combineCycleData.py``` 

if you want to try pulling and aggregating the (post-2014) journey data from TfL!

After that you'd run: 

```python tfl_project/cycle_journey_prep/clean_combined_cycle_data.py``` 

to clean it, but again this is a very slow step.

See _tfl_project/cycle_journey_prep/README_cyclejourneys.md_ for more info.
### A note on station data and database creation
This was fetched especially for the project and is too large to commit. Unfortunately the full functionality of the repo 
will not be available without it, although you are welcome to ask me for a copy of the station data.  

### Demo simulation
You can run, for example: 
```python -m tfl_project.simulation.scenario_scripts.sim1_warehouses_bigger_5am``` 
to perform simulations and get resulting output files.

If you're using the terminal or cmd, it's necessary to run it as a module, as above.

This is possible because I committed the contents of _tfl_project/simulation/files/pickled_cities/london_warehouses_ to 
version control... the equivalent of "here's one I made earlier"

Some scripts such as _sim0_base_5am_no_rebal.py_ won't work out of the box unless you have prepared the database 
accordingly: the pre-prepared cities are large files so weren't all put in version control.

### API requests
With a little work you will be able to run, if you wish: ```python -m tfl_project.tfl_api_logger.bikeStationStatus``` to see the 
result of a single request and log. Run it as a module, as above.

In reality this was actually run by a cron job as scheduled, see _tfl_project/tfl_api_logger/README_api_log.md_
for more details.

Two prerequisite actions are:
* You get a tfl token and save it as _tfl_api_logger/apiCredentials.txt_ 
(ID on first line, token on second line)
* You change `out_csv` to an actual location available on your machine. 

See _tfl_project/tfl_api_logger/README_api_log.md_ for more info.