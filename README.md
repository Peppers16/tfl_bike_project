# tflStatusLog
## Periodically gathering line status information from the TFL Unified API. 

### TODO
1. Make the creation of a new Google Spreadsheet reproducible... or at least 
document the manual preparation of a sheet. 
2. Tests for simple_timed_loop() and request_and_format() and log_to_google()
3. Add failsafes if API requests fail or internet is down. Bare minimum should be to skip the log rather than crash 
the code.

### You will need:
#### Setup TFL API
1. Open a [TFL API](https://api-portal.tfl.gov.uk) account
    1. Save a file in the working directory called `apiCredentials.txt` which lists:
        * your TFL API ID on the first line
        * your TFL API key on the second line
#### Setup Google Sheets API (for logging data) 
2. To enable the [Google Sheets API](https://developers.google.com/sheets/api/quickstart/python) on your Google account.
    1. Save the 'client configuration' to the working directory as `googleCredentials.json`
    2. In the Terminal / CMD run: 
        ```bash
        pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib
        ```
        (you'll need to install pip first if you don't have it)
    3. Run googleSheetsAccess.py as per [Google's instructions](https://developers.google.com/sheets/api/quickstart/python)
        * Note: the first time you do this you have to authenticate with the Google Account, on the device you are using. 
        This involves a webpage opening.
#### Important: API Credentials:
At this stage, you will need to save your TFL credentials to a text file in the directory.
This is a temporary measure to avoid having to hard-code credentials, or request them each time. 

Code currently expects an 'apiCredentials.txt' file with ID on the first line, and key on the second line. 

'apiCredentials.txt' is added to .gitignore. Don't forget to update accordingly if you save file 
by a different name.

#### simpleTimedLoop()
This loop will call the main() function to save status to CSV every (15) minutes from the hour. 
Need to implement some sort of error catching and reporting functionality.
Ideally, a Raspberry Pi will be set to execute this script upon boot. 
