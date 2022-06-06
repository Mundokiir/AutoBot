"""Module to send path tests via ***"""
import random
import string
import time
import json
import calendar
import datetime
import boto3
import requests
from scripts.get_secret import get_secret  # pylint: disable=import-error

# Need to have secrets available before any other execution happens.
secrets = get_secret()


def store_test_info(ebid: int, delivery_url: str, channel_id: str) -> None:
    """Stores incidentID (ebid), Calculated TTL, Delivery URL and Channel ID for future lookup"""
    ttl_time = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    ttl_utc_time = calendar.timegm(ttl_time.utctimetuple())

    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("autobot_path_testing")
    table.put_item(
        Item={
            "id": ebid,
            "TTL": ttl_utc_time,
            "delivery_url": delivery_url,
            "channel_id": channel_id,
        }
    )


def do_say(thing: str, say: object) -> None:
    """Does a "say" to slack while printing that say to the logs"""
    print(f"Doing say: {thing}")
    say_response = say(thing)
    return say_response


def send_notification(slack_users: list, test_type: str, stack: str) -> dict:
    """Sends notification via *** through *****. Doing it this way allows for response subscriptions."""
    random_id = "".join(random.choice(string.ascii_lowercase) for _ in range(10))
    if stack == "US":
        api_endpoint = "https://*****-ingestion.*****************.net/*****/v1/ingestion/itsm"
        auth_key = secrets["*****_key_us"]
    if stack == "EU":
        api_endpoint = "https://*****-ingestion.*****************.eu/*****/v1/ingestion/itsm"
        auth_key = secrets["*****_key_eu"]

    header_data = {"Authentication": auth_key}
    notification_data = {
        "header": {"sourceSystemType": "AutoBot"},
        "incidentDetails": {
            "send": test_type,
        },
        "overrideRecipients": {"contactType": "EXTERNAL_ID", "contacts": slack_users},
        "sourceSystemIncidentInfo": {"incidentID": random_id},
    }
    payload = {}
    print(f"Sending the following notification payload to ***: {notification_data.items()}")
    try:
        response = requests.post(api_endpoint, headers=header_data, json=notification_data)
    except BaseException as err:
        payload["ok"] = False
        payload[
            "message"
        ] = f"I encountered an error connecting to ***** :trynottocry:\nThis likely means the notification wasn't sent. Here's the error:\n```{err}```"
        print(f"Received error connecting:\n{err}")
        return payload

    print(f"Received the following response from ***: {json.dumps(response.text, indent=4)}")

    try:
        status = response.json()["status"]
    except:
        payload["ok"] = False
        payload[
            "message"
        ] = f"I received an unexpected response from ***** :trynottocry:\nThis likely means the notification wasn't sent. Specifically I was unable to detect a 'status' field on the initial response. Here's what I received:\n```{response.text}```"
        return payload

    if status != "INPROGRESS":
        payload["ok"] = False
        payload[
            "message"
        ] = f"I received an unexpected response from ***** :trynottocry:\nThis likely means the notification wasn't sent. Specifically, ***** did not indicate that the incident is in progress like we expect it to. Here's what I received:\n```{response.text}```"
        return payload

    # This delay helps ensure the notification/incident actually kicked off. Might need to increase.
    # We don't receive the delivery details URL or incidentID until the second query.
    print("Waiting 3 seconds to retrieve incidentID")
    time.sleep(3)

    try:
        updated_response = requests.get(f"{api_endpoint}/status/{random_id}", headers=header_data)
        print(
            f"Received the following response from ***: {json.dumps(updated_response.text, indent=4)}"
        )
    except BaseException as err:
        payload["ok"] = False
        payload = {
            "message": f"I encountered an error connecting to ***** on the followup, which is required to obtain incident information. :trynottocry:\nThis likely means the notification wasn't sent. Here's the error:\n```{err}```"
        }
        print(f"Received error connecting:\n{err}")
        return payload

    try:
        status = updated_response.json()["incidentStatus"]
    except:
        payload["ok"] = False
        payload[
            "message"
        ] = f"I received an unexpected response from ***** :trynottocry:\nThis likely means the notification wasn't sent. Specifically I was unable to detect a 'incidentStatus' field on the second response. Here's what I received:\n```{updated_response.text}```"
        return payload

    if status == "NOTCREATED":
        payload["ok"] = False
        payload[
            "message"
        ] = f"***** indicates that the incident is stuck on 'NOTCREATED' status. :trynottocry:\nThis usually mean the payload we sent to ***** could not be processed. Did someone mess with the Webhook configs? \nThis basically guarantees that the notification wasn't sent. Here's the response I received:\n```{response.text}```"
        return payload

    for i in range(1, 3):
        try:
            incident_id = updated_response.json()["*****************ID"]
            delivery_url = updated_response.json()["deliveryDetailsURL"]
        except:
            print(f"Failed to detect either incidentID or deliveryURL, backing off for {i} seconds...")
            time.sleep(i)
            continue
        else:
            if incident_id is None or delivery_url is None:
                payload["ok"] = False
                payload[
                    "message"
                ] = f"I was unable to obtain an incidentID or the deliveryDetailsURL from ***** :trynottocry:\nThis could mean an invalid contact was used. Try using the 'update' keyword to update your contact info.\n\nIt's possible the notification wasn't sent, but even if it was I wont be able to properly detect confirmations, even if they are working. Here's what I received from *****:\n```{response.text}```"
                return payload
            else:
                payload["ok"] = True
                payload["incident_id"] = incident_id
                payload["delivery_url"] = delivery_url
                payload["message"] = "ok"
                return payload


def path_test(options, uid, channel, say):
    """Sends SMS/Email/Voice messages from *** to confirm messages are leaving the platform"""
    paths = []
    stacks = []
    users = []
    users.append(uid)
    bad_options = []

    for opt in options:
        if opt[0] == "<" and opt[-1] == ">":
            users.append(opt[2:-1])
        elif opt.casefold() == "test":
            pass  # Don't want this going into bad_options
        elif opt.casefold() == "sms":
            paths.append("SMS")
        elif opt.casefold() == "voice":
            paths.append("VOICE")
        elif opt.casefold() == "email":
            paths.append("EMAIL")
        elif opt.casefold() == "us":
            stacks.append("US")
        elif opt.casefold() == "eu":
            stacks.append("EU")
        else:
            bad_options.append(opt)

    paths_to_send = ", ".join(paths)
    users.remove(
        "*****************"
    )  # This is the BOT user and gets added to the list from the user tagging it. We don't want that.
    users_to_send = ">, <@".join(users)
    users_to_send = "<@" + users_to_send + ">"
    if len(stacks) == 0:  # If no stack is specified, default to US
        stacks.append("US")
    stacks_trimmed = set(stacks) # To ensure that we are only sending to 2 stacks maximum
    stacks_to_send = ", ".join(stacks_trimmed)

    if len(bad_options) > 0:
        bad_options_string = ", ".join(bad_options)
        response = f'Sorry <@{uid}>, you seem to have included the following invalid options:\n{bad_options_string}\n\nValid options are "SMS", "Email", and "Voice". You may also specify a stack ("US" or "EU"), and tag additional CloudOps members to include them.\nNo message has been sent. Please try again.'
        do_say(response, say)
    elif len(paths) == 0:
        response = 'You don\'t seem to have specified a path. Valid options are "SMS", "Email", and "Voice".'
        do_say(response, say)
    elif len(stacks) > 2:
        response = f"You seem to have entered more than 2 production stack options. To avoid excessive messages, we only accept 2 maximum. You entered:\n{stacks}\n\nNo message has been sent. Please try again."
        do_say(response, say)
    else:
        response = f"Sending a test message to following path(s):\n{paths_to_send}.\n\nTo the following users:\n{users_to_send}\n\nFrom the following stack(s): {stacks_to_send}\n"
        do_say(response, say)
        results = []
        urls_list = []
        for path in paths:
            if path == "SMS":
                for stack in stacks_trimmed:
                    sms_result = send_notification(users, "sms", stack)
                    if sms_result["ok"] is False:
                        results.append("bad")
                        response = f"Error sending SMS from {stack} stack:\n{sms_result['message']}"
                        do_say(response, say)
                    else:
                        print(
                            f"Storing info in DB:\nincident_id: {sms_result['incident_id']}\ndelivery_url: {sms_result['delivery_url']}\nchannel: {channel}"
                        )
                        store_test_info(
                            int(sms_result["incident_id"]), sms_result["delivery_url"], channel
                        )
                        urls_list.append(
                            {"stack": stack, "type": "SMS", "url": sms_result["delivery_url"]}
                        )
            elif path == "VOICE":
                for stack in stacks_trimmed:
                    voice_result = send_notification(users, "voice", stack)
                    if voice_result["ok"] is False:
                        results.append("bad")
                        response = (
                            f"Error sending Voice from {stack} stack:\n{voice_result['message']}"
                        )
                        do_say(response, say)
                    else:
                        print(
                            f"Storing info in DB:\nincident_id: {voice_result['incident_id']}\ndelivery_url: {voice_result['delivery_url']}\nchannel: {channel}"
                        )
                        store_test_info(
                            int(voice_result["incident_id"]), voice_result["delivery_url"], channel
                        )
                        urls_list.append(
                            {"stack": stack, "type": "Voice", "url": voice_result["delivery_url"]}
                        )
            elif path == "EMAIL":
                for stack in stacks_trimmed:
                    email_result = send_notification(users, "email", stack)
                    if email_result["ok"] is False:
                        results.append("bad")
                        response = (
                            f"Error sending Email from {stack} stack:\n{email_result['message']}"
                        )
                        do_say(response, say)
                    else:
                        print(
                            f"Storing info in DB:\nincident_id: {email_result['incident_id']}\ndelivery_url: {email_result['delivery_url']}\nchannel: {channel}"
                        )
                        store_test_info(
                            int(email_result["incident_id"]), email_result["delivery_url"], channel
                        )
                        urls_list.append(
                            {"stack": stack, "type": "Email", "url": email_result["delivery_url"]}
                        )
        if "bad" in results:
            response = "One or more errors have occurred sending to ***. Please see above errors. Any paths that did not report an error were successfully sent!"
            do_say(response, say)
        else:
            response_2 = "\n".join([f"{i['stack']} Stack {i['type']}: <{i['url']}|Click Here for Delivery Report>" for i in urls_list])
            response = (
                f"Successfully sent all requested notifications! :data_party:\n\nHere are the available notification reports. I will let you know if/when I receive any confirmations.\n{response_2}"
            )
            do_say(response, say)
