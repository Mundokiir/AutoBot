# AutoBot

### The AutoBot!

This is the repository for the Ops Utility Bot. The AutoBot performs several common functions for both members of CloudOps as well as the ***************** team at large. These functions include:  
- Path Testing - Send SMS, Voice and Email test notifications to ensure messages are leaving the *** platform. (Keyword: "test")
- Confirmation Testing - Using the above keyword, confirmations are posted to the channel the command was invoked from.
- Telq Testing - Send SMS tests to TelQ test endpoints to ensure SMS messages are successfully delivered to various locations. (Keyword: "telq")
- SMS Primary Switching - Check and switch primary and second SMS providers
- Contact Updater - Update *** contact information from Slack for use with path testing. (Keyword: "update")
- On/Off-Boarding - Quick On and Off boarding for new or leaving members of SaaSOps (CloudOps Only).

This version of the bot is for demonstration purposes and is heavily cut down/pruned from its live version for all the obvious reasons.

### Usage
To use the AutoBot, simply tag "@AutoBot" in Slack, followed by one of the function keywords, and any other inputs as required by that particular keyword. The bot must be tagged first and your keyword must be second.  
Here's an example:  
![Usage Example](https://i.imgur.com/386pTAg.png)
## Important Files:
- **lambda-function.py** - The primary lambda function handler. All calls to the bot pass through this, except for confirmations/response subscriptions.
- **response_sub_handler.py** - A separate lambda function is deployed that catches the webhook messages from *** when a contact sends confirmation. This file handles that.
- scripts/ - Most functions get their own file in this folder
  - **contact.py** - The *** Contact Updater.
  - **onboarding.py** - On/Off Boarding Automation.
  - **pathtest.py** - SMS, Voice and Email Path Testing.
  - **telq.py** - TelQ SMS Testing.
  - **smsprimary.py** - Reporting on (and switching of) primary/secondary SMS service providers
  - **services** - This folder contains the classes for all the various services a user may need to be on or offboarded in.

All other folders and files are third party modules required for the bot to function.

### Response Subscriptions/Confirmation Reporting
To facilitate reporting on received confirmations, the bot has been changed so that it no longer sends standard *** notifications via the standard *** API and instead sends incidents via the ***** API. This allows us to use "Response Subscriptions" in *** to send event data to a lambda function when we receive a confirmation.

This has resulted in needing a separate lambda function to receive this data and THIS means we have to facilitate passing information on the back end. As such:
- We now have a DynamoDB table in AWS (managed via Terraform of course) in which we dump information about the request:
  - The channel the request was invoked from
  - The "results URL" ***** gives us which contains info about the notifications and confirmations
  - A TTL value one hour in the future that AWS reads to auto-delete the entry from the DB table
- We pull this information using the incidentID as a table key to know where to send our slack message.
# Requirements
### Module Requirements
- Slack 'Bolt' Python SDK
  - slack_bolt - 1.13.0
  - slack_sdk - 3.15.2
- Requests
  - requests - 2.27.1
- Pymongo
  - pymongo - 4.0.0+
- Runtime requirements
  - Python 3.8+
  - Boto3 from AWS (see below)
# Infrastructure
The infrastructure needed to run this code is managed by Terraform/Atlantis.
### AWS Lambda Configuration
This program is intended to run in an AWS lambda environment and requires access to the AWS Secrets manager in order to pull credentials for many functions. It's also configured in "lazy" mode which is required when running on "FaaS" services like Lambda and thus is incompatible with typical methods of running a slack bolt application without major refactoring.

# Logging
All functions of the bot have been configured with fairly robust logging to the cloudwatch log group.