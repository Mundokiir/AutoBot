"""Script to determine or swap the Primary and Secondary SMS service providers for a given stack"""
from datetime import datetime
import pymongo
import requests
from pymongo.errors import ConnectionFailure
from scripts.get_secret import get_secret  # pylint: disable=import-error

# Need to have secrets available before any other execution happens.
secrets = get_secret()


def do_say(thing: str, say: object) -> None:
    """Does a "say" to slack while printing that say to the logs"""
    print(f"Doing say: {thing}")
    say_response = say(thing)
    return say_response


def delete_slack_message(message_id, channel_id):
    """Deletes a slack message for situations in which we have no
    response URL and cannot override previous messages"""
    url = "https://slack.com/api/chat.delete"
    headers = {"authorization": f"Bearer {secrets['token']}"}
    payload = {"channel": f"{channel_id}", "ts": f"{message_id}"}
    response = requests.post(url, json=payload, headers=headers)
    output = response.json()
    return output


def index_in_list(a_list: list, index: int) -> bool:
    """Verifies if a given index exists in a list"""
    return index < len(a_list)


def connect_mongodb(stack):
    """Returns a mongoDB client and database object or None if errors"""
    if stack == "US":
        db_seed = "*****************"
    elif stack == "EU":
        db_seed = "*****************"
    elif stack == "STG":
        db_seed = "*****************"
    db_user = secrets["sms_primary_user"]
    db_pass = secrets["sms_primary_pass"]
    db_name = "*****************"

    uri = f"mongodb+srv://{db_user}:{db_pass}@{db_seed}/?readPreference=secondary&*****************"

    try:
        client = pymongo.MongoClient(uri)
        database = client[db_name]
    except ConnectionFailure as err:
        print("Failed to connect to Mongo DB")
        print(err)
        return (None, None)
    return (client, database)


def validate_country(database, country):
    """Confirms a given country exists in the provided DB"""
    doc1 = database.DB.find({"country": country}, {"countryName": 1})
    if not doc1:
        print("Invalid country code entered")
        return False
    return True


def lookup_primary(country, stack, say) -> tuple:
    """Returns (None,None) if fatal error, (primary,None) or (None,secondary) if one or the other is not found
    or (primary,secondary) if both found successfully."""
    mongo_client, database = connect_mongodb(stack)
    if mongo_client is None:
        print("Error connecting to MongoDB")
        response = (
            "I have encountered an error connecting to MongoDB :trynottocry: I'm unable to proceed."
        )
        do_say(response, say)
        return (None, None)

    # validate the country code
    if validate_country(database, country) is False:
        mongo_client.close()
        print("Country Not Found in DB")
        response = f"I don't seem to be able to find an sms routing entry for {country}. I'm unable to proceed."
        do_say(response, say)
        return (None, None)

    # validation - check to ensure country has both Primary and Secondary vendors
    result_count = database.DB.count_documents({"country": country, "seq": 1})
    if result_count != 1:
        print("Country does not have Primary vendor.")
        primary = None
    result_count = database.DB.count_documents({"country": country, "seq": 2})
    if result_count != 1:
        print("Country does not have Secondary vendor.")
        secondary = None

    doc1 = database.DB.find(
        {"country": country},
        {
            "country": 1,
            "seq": 1,
            "vendor": 1,
            "*****************": 1,
            "countryName": 1,
            "*****************": 1,
            "_id": 1,
            "lastModifiedDate": 1,
        },
    ).sort([("country", pymongo.ASCENDING), ("seq", pymongo.ASCENDING)])

    for i in doc1:
        if int(i["seq"]) == 1:
            primary = {}  # Safe to do in loop since there's only one primary (hopefully)
            primary["vendor"] = i["vendor"]
            primary["countryName"] = i["countryName"]
            primary["*****************"] = i["*****************"]
            primary["lastModifiedDate"] = i["lastModifiedDate"]
        else:
            secondary = {}  # Safe to do in loop since besides the primary there's only a secondary
            secondary["vendor"] = i["vendor"]
            secondary["countryName"] = i["countryName"]
            secondary["*****************"] = i["*****************"]
            secondary["lastModifiedDate"] = i["lastModifiedDate"]
    mongo_client.close()
    return (primary, secondary)


def do_switch(country, stack, say):
    """Does the actual primary/secondary swap task"""
    mongo_client, database = connect_mongodb(stack)
    if mongo_client is None:
        print("Error connecting to MongoDB")
        response = (
            "I have encountered an error connecting to MongoDB :trynottocry: I'm unable to proceed."
        )
        do_say(response, say)
        return None
    try:
        result = database.DB.find({"country": country}, {"seq": 1, "_id": 1})
        for i in result:
            v_seq = int(i["seq"])
            v_id = i["_id"]
            v_last_modified = datetime.now()

            if v_seq == 1:
                database.DB.update_one(
                    {"_id": v_id}, {"$set": {"seq": 2, "lastModifiedDate": v_last_modified}}
                )

            if v_seq == 2:
                database.DB.update_one(
                    {"_id": v_id}, {"$set": {"seq": 1, "lastModifiedDate": v_last_modified}}
                )
    except BaseException as err:
        print(err)
        response = f"I have encountered an error updating the DB:\n{err}"
        do_say(response, say)
        return None
    else:
        return True


def sms_route_check(options, user_id, say):
    """Checks current primary and secondary and returns response to use"""
    # Update this to whatever these companies have changed their name to.
    translation_dict = {
        "*****************": "*****************",
        "*****************": "*****************"
        }

    # Options[0] = "@AutoBot"
    # Options[1] = "primary"
    # Options[2] = Stack
    # Options[3] = Country Code
    if index_in_list(options, 3) is False or index_in_list(options, 4) is True:
        response = f"Sorry <@{user_id}>, You seem to have provided the wrong number of options!\n\nThis keyword takes *exactly 2* arguments:\n1) An *** Production stack: [*US*, *EU*, *STG*] to check.\n2) A 2 letter country code.\n\nExample: `@AutoBot primary EU IN`\n\nTry `@AutoBot primary help` for help."
        do_say(response, say)
        return
    if options[2].casefold() not in ["us", "eu", "stg"]:
        response = f"Sorry <@{user_id}>, You have specified an invalid application stack. Valid options are [*US*, *EU*, *STG*].\n\nExample: `@AutoBot primary STG IN`\nTry `@AutoBot primary help` for help."
        do_say(response, say)
        return
    if options[2].casefold() == "stg":
        response = f"Sorry <@{user_id}>, I cannot currently look up the primary/secondary in stage. Please contact CloudOps for assistance."
        do_say(response, say)
        return
    if len(options[3]) != 2:
        response = f"Sorry <@{user_id}>, You must specify the 2 letter country code.\n\nExample: `@AutoBot primary us us`\n\nTry `@AutoBot primary help` for help."
        do_say(response, say)
        return

    country = options[3].upper()
    stack = options[2].upper()
    primary, secondary = lookup_primary(country, stack, say)
    if primary is None and secondary is None:
        return

    response = f"*Provider Information for {primary['countryName']} in the {stack} Stack*:"
    do_say(response, say)

    if primary is None:
        response = "I could not locate a primary vendor (seq = 1)."
        do_say(response, say)
    else:
        response = f"Primary: *{translation_dict[primary['vendor']]}*. MT Code: *{primary['*****************']}*. Last Modified: {primary['lastModifiedDate']}"
        do_say(response, say)

    if secondary is None:
        response = "I could not locate a secondary vendor (seq = 2)."
        do_say(response, say)
    else:
        response = f"Secondary: *{translation_dict[secondary['vendor']]}*. MT Code: *{secondary['*****************']}*. Last Modified: {secondary['lastModifiedDate']}"
        do_say(response, say)

    response = "This is what is in the database. I cannot guarantee the connectors are respecting this preference."
    do_say(response, say)


def switch_sms_primary(options: list, user_id: str, say: object):
    """Handles switching primary and secondary providers.
    Sends an "are you sure" prompt which is handled later."""
    # Options[0] = "@AutoBot"
    # Options[1] = "primary"
    # Options[2] = "switch"
    # Options[3] = Stack
    # Options[4] = Country Code
    if index_in_list(options, 4) is False or index_in_list(options, 5) is True:
        response = f"Sorry <@{user_id}>, You seem to have provided the wrong number of options!\n\nThis action takes *exactly 2* arguments:\n1) An *** Production stack: [*US*, *EU*, *STG*] to send from.\n2) A 2 letter country code.\n\nExample: `@AutoBot primary switch EU IN`\n\nTry `@AutoBot primary help` for help."
        do_say(response, say)
        return
    if options[3].casefold() == "stg":
        response = f"Sorry <@{user_id}>, I cannot currently switch the primary/secondary in stage."
        do_say(response, say)
        return
    if options[3].casefold() not in ["us", "eu"]:
        response = f"Sorry <@{user_id}>, You have specified an invalid application stack. Valid options are [*US*, *EU*].\n\nExample: `@AutoBot primary switch US MX`\nTry `@AutoBot primary help` for help."
        do_say(response, say)
        return
    if len(options[4]) != 2:
        response = f"Sorry <@{user_id}>, You must specify a 2 letter country code.\n\nExample: `@AutoBot primary switch us us`\n\nTry `@AutoBot primary help` for help."
        do_say(response, say)
        return

    country = options[4].upper()
    stack = options[3].upper()
    primary, secondary = lookup_primary(country, stack, say)

    if primary is None or secondary is None:  # If either is none, we can't really switch can we?
        response = f"Sorry <@{user_id}>, it doesn't look like {country} has both a Primary *and* a Secondary vendor for me to swap."
        do_say(response, say)
        return

    # Send an "are you sure"
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Switching Primary/Secondary for {primary['countryName']} in {stack} stack.",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"Confirm you want to swap the current primary and secondary SMS providers for {primary['countryName']}.",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "emoji": True, "text": "Approve"},
                    "confirm": {
                        "title": {"type": "plain_text", "text": "Are you sure?"},
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Confirm switching the primary SMS provider for {primary['countryName']} in the {stack} stack.",
                        },
                        "confirm": {"type": "plain_text", "text": "Do it"},
                        "deny": {"type": "plain_text", "text": "Stop, I've changed my mind!"},
                    },
                    "style": "primary",
                    "value": f"{stack} {country}",  # We do a text.split() on this field to pull the stack and country in one swoop
                    "action_id": "switch_primary_sms",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "emoji": True, "text": "Deny"},
                    "style": "danger",
                    "value": "deny",
                    "action_id": "switch_primary_sms_nevermind",
                },
            ],
        },
    ]
    say(blocks=blocks)


def handle_primary_switch(body, say):
    """Triggered when someone confirms the "are you sure" prompt
    Actually calls the switch function"""
    # Container section of the body has message ID and channel ID needed to delete the block we sent previously
    container = body["container"]
    channel_id = container["channel_id"]
    message_id = container["message_ts"]

    # Actions section of body contains the values of the button(s) the user clicked, which we parse for first_name, last_name and email
    actions = body["actions"]  # Returns a list
    actions_payload = actions[0]  # Returns dict
    encoded_info = actions_payload["value"]  # Value attached so the button click
    options = encoded_info.split()
    stack = options[0]
    country = options[1]
    print(f"Detected Options:\nStack: {stack}\nCountry: {country}")

    delete_slack_message(message_id, channel_id)
    response = f"Swapping Primary/Secondary vendors for {country} in the {stack} stack..."
    do_say(response, say)

    switch_result = do_switch(country, stack, say)
    if switch_result is None:
        response = "Vendor swap failed..."
    else:
        response = f"Successfully swapped primary and secondary vendors for {country} in the {stack} stack.\n\n*WARNING*: The SMS connectors still need to be restarted manually to pick up these changes!"
    do_say(response, say)


def handle_primary_switch_nevermind(body, say):
    """Triggered if the user changes their mind on the "are you sure" prompt"""
    # Container section of the body has message ID and channel ID needed to delete the block we sent previously
    container = body["container"]
    channel_id = container["channel_id"]
    message_id = container["message_ts"]

    delete_slack_message(message_id, channel_id)
    response = "Okay :ok_hand: Not switching vendors for now..."
    do_say(response, say)
