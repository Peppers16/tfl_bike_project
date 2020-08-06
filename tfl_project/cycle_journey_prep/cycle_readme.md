# TFL Cycle Data
## Overview
The TFL [open data page for cycling](https://cycling.data.tfl.gov.uk/) has data for _all_ Santander Bike journeys.
They're saved as CSVs. 

Initially my task is to download all these CSVs them combine them into one dataset.

## combineCycleData 

Downloading this data has a little bit of overhead:
* 2015 onwards are listed as individual CSVs (with individual download links)
* 2012-2014 have zip files which can be downloaded in bulk.

My process was as follows:
1. Designate a directory for all the CSV files to be saved to: `tfl_project\data\cycle_journeys`
2. Manually download then extract the 2012-2014 CSVs to that location (not too much overhead) 
3. Use a python script to individually download all the 2015-onwards CSVs to the same location
    * Note: There was a little bit of manual overhead here: save the webpage HTML as **cycling.data.tfl.gov.uk.html** to 
    the cycleJourneys subdirectory which you are currently in... I extracted the URLs from this. 
4. `download_csvs_matching_regex()` was used to extract links from the HTML which matched the cycle journey format. The 
function requests and saves each CSV in turn.
5. ...combine CSVs... 
6. ...clean CSVs...

### Further details
This project takes the HTML from the TFL webpage: https://cycling.data.tfl.gov.uk/ in order to generate a list of (links)
to the cycling datasets.

**This requires the manual step of saving the page as an html file to this directory**. Simple requests don't load the 
required links, so simply accessing the page manually in a browser then saving the page it is easiest. If updating, you
can simply overwrite with a fresh copy.  


##### Important piece of data cleansing which was performed manually:
The following piece of data cleansing was performed manually:
'134JourneyDataExtract31Oct2018-06Nov2018.csv' was the only csv to have a column 'EndStation Logical Terminal' instead 
of 'EndStation ID'. The former had different values but the same descriptions as the latter. 
I manually performed the following steps in Excel:
1. Use 'StartStation Desc' as a key for 'StartStation ID'
2. Use 'EndStation Name' as a search key for 'StartStation ID'
3. Replace 'EndStation Logical Terminal' with the resulting column, and rename to 'EndStation ID'

These steps were quick to perform, and I felt it would take too much time to program around this single fringe case.
