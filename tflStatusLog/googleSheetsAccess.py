from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


# If modifying these scopes, delete the file token.pickle.
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# The ID and range of a sample spreadsheet.
# SAMPLE_SPREADSHEET_ID = '1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms'
# SAMPLE_RANGE_NAME = 'Class Data!A2:E'


def authenticate_with_google():
    """authenticates with Google. First time may cause a browser window to open.
    then builds service object for interacting with Google Sheets API (v4) """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'googleCredentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('sheets', 'v4', credentials=creds)


def log_to_google(values_to_add, spreadsheet_id):
    """Authenticates Google Sheets access, if required.
    Then, appends latest values to the predefined google Spreadsheet
    Values_to_add is a list of lists, where each list is a row.
    """
    service = authenticate_with_google()

    body = {'values': values_to_add}

    result = service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id
        , range='A1'
        , body=body
        , valueInputOption='USER_ENTERED'
    ).execute()

    updated_range = result['updates']['updatedRange']
    updated_rows = result['updates']['updatedRows']
    print(f"Appended {updated_rows} rows into range {updated_range} in the Google Spreadsheet")
