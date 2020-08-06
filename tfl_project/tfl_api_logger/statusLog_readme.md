# tfl_api_logger
## Periodically gathering line status and bikepoint information from the TFL Unified API. 

This sub-package is unique from the rest in the project because it is concerned with periodic data-gathering 
rather than manipulation of pre-existing data. It could be argued that this should be its own package, separate from 
the other sub-packages in tfl_project. 

This package is:
* **Primarily** used by a raspberry pi device which runs `bikeStationStatus.py` as a script periodically to log data to a csv
* Used once as a module by `tfl_project.create_sqlite_database` which makes an API call to fill in some missing metadata

This subdirectory provides modules for logging line status data (point in time) from the TFL API, then appending it to 
a Google Sheet, a CSV, or both. 

I now primarily use the csv and ignore the Google Sheet. The original motivation for uploading to a Google Sheet was to 
achieve resilience, and also ease of monitoring. 

`statusRequest.py` when run as a script will execute a function called `singleRequest()` once then terminate. Therefore 
a log can be formed by periodically running the script, which I scheduled using Crontab.

The same applies for `bikeStationStatus.py`

**important to note:** currently this module (and also the `googleSheetsAccess` module) make relative references **so 
work when the python interpreter's present directory is `tflProject/tflStatusLog`**. Running the script from the parent
directory `tflProject` will cause errors relating to relative / absolute paths. 

### Getting Started:
#### Setup TFL API
1. Open a [TFL API](https://api-portal.tfl.gov.uk) account
    1. Save a file in the working directory called `apiCredentials.txt` which lists:
        * your TFL API ID on the first line
        * your TFL API key on the second line
#### Setup Google Sheets API (for logging data)
_Note: if you just want to log to a local CSV you can skip to step 1.iv below, replacing True with False_
2. To enable the [Google Sheets API](https://developers.google.com/sheets/api/quickstart/python) on your Google account.
    1. Save the 'client configuration' to the working directory `tflProject/tflStatusLog` as `googleCredentials.json`
    2. In the Terminal / CMD run: 
        ```bash
        pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
        ```
        (you'll need to install pip first if you don't have it)
    3. Run googleSheetsAccess.py as per [Google's instructions](https://developers.google.com/sheets/api/quickstart/python)
        * Note: the first time you do this you have to authenticate with the Google Account, on the device you are using. 
        This involves a webpage opening.
    4. This will create a file called `token.pickle` which should mean that you don't have to manually authenticate in 
    future.
3. Create a Google Sheet in your Google Drive which has the columns: timestamp, lineId, statusSeverity and note the
spreadsheet ID which can be seen as the long alphanumeric string in the browser URL.
4. In the script `statusRequest.py` assign the variable `google_spreadsheet_id` as the spreadsheet ID from the previous
step. E.g.
    ```python
    google_spreadsheet_id = '1j2uY1NJwuTdeCQ2OoFzNDcfTXM7s3OkLvjKa6Wy9PlU'
    ``` 
5. the `main()` function of `statusRequest.py` will log to google by default but you may wish to specify explicitly edit 
the end of the script `statusRequest.py` to look like:
    ```python
    if __name__ == '__main__':
       singleRequest(log_to_google=True) 
    ```
#### Setup CSV for logging
_Note: you can skip this if you are happy to just log to Google_
1. Create a directory on your device for the CSV to be saved to. 

    If you're using an external hard drive on a Linux device 
    then you can [follow these steps](https://www.raspberrypi.org/documentation/configuration/external-storage.md) to
    automatically mount the drive to the same directory upon boot (I did this with my Raspberry Pi)
2.  Edit `statusRequest.py` with the directory plus a CSV name like follows:
    ```python
    csv_file = 'data/statuslog.csv'
    ```
    or, as it looked on my Raspberry Pi:
    ```python
    csv_file = '/mnt/ntfsHDD/tfl_logging/TFL_Status_Log.csv'
    ```
3. At the end of `statusRequest.py` add `log_to_csv = True` to the main call. E.g.
    ```python
    if __name__ == '__main__':
       singleRequest(log_to_csv=True)  # may also have log_to_google = True
    ```
4. If the given CSV file does not exist in that directory then the script will create it for you before logging. 
If it already exists then it will append to it. 
#### Run the script periodically to log data
##### By a scheduler like crontab
The best and most robust way to do this is to make a scheduler run `statusRequest.py` periodically. This will execute 
`singleRequest()` each time. I used a crontab on a Linux device (Raspberry Pi) to run the script on every 15th minute. 

```bash
crontab -e  # edit the crontab file
```
then at the end of the crontab file add something like the following:
```bash
*/15 * * * * cd /home/pi/tflProject/tfl_project/tfl_api_logger && /usr/bin/python3 statusRequest.py 2> cronOut.txt
```
Noting the following parameters which you'll need to replace as per your setup:
 * `*/15 * * * * *` says to call every 15th minute. You can edit as required. 
 * `cd /home/pi/tflProject/tfl_project/tfl_api_logger` change directory to wherever your repository is saved. Make sure to specify the 
 `tflStatusLog` subdirectory where `statusRequest.py` is stored. 
 * `/usr/bin/python3` is the actual location of the python interpreter. Usually you'd just call `python3` or `python` 
 but crontab doesn't always have environmental variables like this available. 
 * `2> cronOut.txt` indicates that an error will be saved to a text file if one occurs. Useful for debugging.
##### By a Python loop:
For slightly less overhead, you can alternatively modify `statusRequest.simple_timed_loop()` and set this running in python, as a background 
process if you like. This will also log every n/th minute, but isn't recommended for long-term logging because a 
single Exception (e.g. failed to connect to API) will end the process.

