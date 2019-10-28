# tflStatusLog
## Periodically gathering line status information from the TFL Unified API. 

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
