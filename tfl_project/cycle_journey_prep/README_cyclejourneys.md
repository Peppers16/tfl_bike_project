# TFL Cycle Data
## Overview
The TFL [open data page for cycling](https://cycling.data.tfl.gov.uk/) has data for _all_ Santander Bike journeys.
They're saved as CSVs. 

Initially my task is to download all these CSVs them combine them into one dataset. There is then a separate script to 
clean this combined dataset.

## Instructions
1. Designate a directory for all the CSV files to be saved to: `tfl_project\data\cycle_journeys`
2. If you want pre-2015 data: manually download then extract the 2012-2014 CSVs (bulk file on TfL's webpage) to that location 
3. If you wish to fetch up to the _ very latest_ (i.e. post-August 2020) journey data, then replace the `cycling.data.tfl.gov.uk.html` file with the 
latest webpage: visit The TFL [web page](https://cycling.data.tfl.gov.uk/) and 'save page' to this subdirectory.  
4. Run ```python cycle_journey_prep/combineCycleData.py``` to download all the journey data CSVs and combine them. 
Once you have `JourneysDataCombined.csv` you are free to delete the individual CSVs
5. Run ```python cycle_journey_prep/clean_combined_cycle_data.py``` to clean the cycle data as receive 
`JourneysDataCombined_CLEANSED.csv` 

