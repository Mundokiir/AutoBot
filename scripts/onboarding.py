"""CloudOps Only utility to quickly on/offboard members of SaaSOps"""
import re
import requests
from scripts.get_secret import get_secret  # pylint: disable=import-error
from scripts.services.datadog import DataDogOnBoarder  # pylint: disable=import-error
from scripts.services.alertsite import AlertSiteOnBoarder  # pylint: disable=import-error
from scripts.services.sumologic import SumoLogicOnBoarder  # pylint: disable=import-error
from scripts.services.digicert import DigiCertOnBoarder  # pylint: disable=import-error

# Need to have secrets available before any other execution happens.
secrets = get_secret()


def do_say(thing: str, say: object) -> object:
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


def onboard(options: list, user_id: str, say: object) -> None:
    """Primary onboard function handler"""
    if index_in_list(options, 3) is False or index_in_list(options, 5) is True:
        response = f"Sorry <@{user_id}>, You seem to have provided the wrong number of options!\n\nThis keyword takes two (2) arguments: *First Name* and *Last Name*.\n\nExample: `@AutoBot onboard Billie Jean.`\n\nYou can optionally supply a custom email address as a third argument if different than usual.`\nTry `@AutoBot onboard help` for help."
        do_say(response, say)
        return
    first_name = options[2].title()
    last_name = options[3].title()
    if index_in_list(options, 4) is True:  # options[4] is likely to be a custom email address
        email = re.search("mailto:(.+)\|", options[4].lower())  # pylint: disable=anomalous-backslash-in-string
        if email is None:
            response = f"Sorry <@{user_id}>, I'm having trouble deciphering the email you've specified. Note that you may only offboard `@*****************.com` email addresses.\n\nYou specified: {options[2]}\n\nExample: `@AutoBot onboard Billie Jean billie.jean@*****************.com`\n\nTry `@AutoBot onboard help` for help."
            do_say(response, say)
            return
        else:
            email = email.group(1)
        if "@*****************.com" not in email[-15:]:
            response = f"Sorry <@{user_id}>, You may only onboard `@*****************.com` email addresses!\nYou specified '{options[4]}'\n\nExample: `@AutoBot onboard Billie Jean billie.jean@*****************.com`\n\nTry `@AutoBot onboard help` for help."
            do_say(response, say)
            return
        elif "@" in options[2] or "@" in options[3]:
            response = f"Sorry <@{user_id}>, You may possibly be trying to specify things in the wrong order...\nYou specified the following values, please double check and try again:\nFirst Name: {first_name}\nLast Name: {last_name}\nEmail Address: {email}\n\nExample: `@AutoBot onboard Billie Jean billie.jean@*****************.com`\n\nTry `@AutoBot onboard help` for help."
            do_say(response, say)
            return
        elif email == "*****************":
            response = f"Sorry <@{user_id}>, I cannot on/offboard ***************** it would break stuff."
            do_say(response, say)
            return
        response = (
            f'Starting the onboarding process for "{first_name} {last_name}", using "{email}."'
        )
        do_say(response, say)
    else:
        email = None
        response = f"Starting the onboarding process for \"{first_name} {last_name}\", using computed email \"{first_name.lower()+'.'+last_name.lower()+'@*****************.com'}.\""
        do_say(response, say)

    onboarder_list = []
    if email:
        datadog = DataDogOnBoarder(
            api_key=secrets["DD-API-KEY"],
            app_key=secrets["DD-APPLICATION-KEY"],
            first_name=first_name,
            last_name=last_name,
            email=email,
        )
        alertsite = AlertSiteOnBoarder(
            user=secrets["alertsite_user"],
            passwd=secrets["alertsite_pass"],
            first_name=first_name,
            last_name=last_name,
            email=email,
        )
        sumologic = SumoLogicOnBoarder(
            access_id=secrets["sumo_access_id"],
            access_key=secrets["sumo_access_key"],
            first_name=first_name,
            last_name=last_name,
            email=email,
        )
        digicert = DigiCertOnBoarder(
            api_key=secrets["digicert_api_key"],
            first_name=first_name,
            last_name=last_name,
            email=email,
        )
    else:
        datadog = DataDogOnBoarder(
            api_key=secrets["DD-API-KEY"],
            app_key=secrets["DD-APPLICATION-KEY"],
            first_name=first_name,
            last_name=last_name,
        )
        alertsite = AlertSiteOnBoarder(
            user=secrets["alertsite_user"],
            passwd=secrets["alertsite_pass"],
            first_name=first_name,
            last_name=last_name,
        )
        sumologic = SumoLogicOnBoarder(
            access_id=secrets["sumo_access_id"],
            access_key=secrets["sumo_access_key"],
            first_name=first_name,
            last_name=last_name,
        )
        digicert = DigiCertOnBoarder(
            api_key=secrets["digicert_api_key"], first_name=first_name, last_name=last_name
        )
    onboarder_list.append(datadog)
    onboarder_list.append(alertsite)
    onboarder_list.append(sumologic)
    onboarder_list.append(digicert)

    for service in onboarder_list:
        onboard_result = service.onboard()
        response = onboard_result["message"]
        do_say(response, say)

    response = "Onboarding process completed! :party_chewbacca:"
    do_say(response, say)


def offboard(first_name, last_name, email, say) -> None:
    """Primary offboard function handler"""
    offboarder_list = []

    datadog = DataDogOnBoarder(
        api_key=secrets["DD-API-KEY"],
        app_key=secrets["DD-APPLICATION-KEY"],
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    alertsite = AlertSiteOnBoarder(
        user=secrets["alertsite_user"],
        passwd=secrets["alertsite_pass"],
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    sumologic = SumoLogicOnBoarder(
        access_id=secrets["sumo_access_id"],
        access_key=secrets["sumo_access_key"],
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    digicert = DigiCertOnBoarder(
        api_key=secrets["digicert_api_key"], first_name=first_name, last_name=last_name, email=email
    )

    offboarder_list.append(datadog)
    offboarder_list.append(alertsite)
    offboarder_list.append(sumologic)
    offboarder_list.append(digicert)

    for service in offboarder_list:
        offboard_result = service.offboard()
        response = offboard_result["message"]
        do_say(response, say)

    response = "Offboarding process completed! :bye_boo:"
    do_say(response, say)


def kickoff_offboard(options: list, user_id: str, say: object):
    """Triggers the offboarding process after parsing and verifying user input
    Assuming all is well, this function will send an "are you sure" prompt to be handled later"""
    if index_in_list(options, 3) is False or index_in_list(options, 5) is True:
        response = f"Sorry <@{user_id}>, You seem to have provided the wrong number of options!\n\nThis keyword takes two (2) arguments: *First Name* and *Last Name*.\n\nExample: `@AutoBot offboard Billie Jean.\n\nYou can optionally supply a custom email address as a third argument if different than usual.`\nTry `@AutoBot offboard help` for help."
        do_say(response, say)
        return
    first_name = options[2].title()
    last_name = options[3].title()
    if index_in_list(options, 4) is True:  # options[4] is likely to be a custom email address
        email = re.search("mailto:(.+)\|", options[4].lower())  # pylint: disable=anomalous-backslash-in-string
        if email is None:
            response = f"Sorry <@{user_id}>, I'm having trouble deciphering the email you've specified. Note that you may only offboard `@*****************.com` email addresses.\n\nYou specified: {options[2]}\n\nExample: `@AutoBot offboard Billie Jean billie.jean@*****************.com`\n\nTry `@AutoBot offboard help` for help."
            do_say(response, say)
            return
        else:
            email = email.group(1)
        if "@*****************.com" not in email[-15:].casefold():
            response = f"Sorry <@{user_id}>, You may only offboard `@*****************.com` email addresses!\nYou specified '{options[4]}'\n\nExample: `@AutoBot offboard Billie Jean billie.jean@*****************.com`\n\nTry `@AutoBot offboard help` for help."
            do_say(response, say)
            return
        elif "@" in options[2] or "@" in options[3]:
            response = f"Sorry <@{user_id}>, You may possibly be trying to specify things in the wrong order...\nYou specified the following values, please double check and try again:\nFirst Name: {first_name}\nLast Name: {last_name}\nEmail Address: {email}\n\nExample: `@AutoBot offboard Billie Jean billie.jean@*****************.com`\n\nTry `@AutoBot offboard help` for help."
            do_say(response, say)
            return
        elif email == "*****************":
            response = f"Sorry <@{user_id}>, I cannot on/offboard *****************, it would break stuff."
            do_say(response, say)
            return
    else:
        email = f"{first_name.lower()}.{last_name.lower()}@*****************.com"
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Please confirm you want to offboard {first_name} {last_name}!",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"This will *destroy* the user {email} and there is no easy way to undo this!",
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
                            "text": "You will be deleting the user from CloudOps Systems, there's no undo...",
                        },
                        "confirm": {"type": "plain_text", "text": "Do it"},
                        "deny": {"type": "plain_text", "text": "Stop, I've changed my mind!"},
                    },
                    "style": "primary",
                    "value": f"{first_name} {last_name} {email}",  # We do a text.split() on this field to pull the first last and email in one swoop
                    "action_id": "offboard_request",
                },
                {
                    "type": "button",
                    "text": {"type": "plain_text", "emoji": True, "text": "Deny"},
                    "style": "danger",
                    "value": "deny",
                    "action_id": "offboard_nevermind",
                },
            ],
        },
    ]

    say(blocks=blocks)


def handle_offboarding(body, say):
    """Triggers when the user confirms the "are you sure" prompt"""
    # Container section of the body has message ID and channel ID needed to delete the block we sent previously
    container = body["container"]
    channel_id = container["channel_id"]
    message_id = container["message_ts"]

    # Actions section of body contains the values of the button(s) the user clicked, which we parse for first_name, last_name and email
    actions = body["actions"]  # Returns a list
    actions_payload = actions[0]  # Returns dict
    encoded_info = actions_payload["value"]  # Value attached to the button click
    options = encoded_info.split()
    first_name = options[0]
    last_name = options[1]
    email = options[2]
    print(f"Detected Options:\nFirst Name: {first_name}\nLast Name: {last_name}\nEmail: {email}")

    delete_slack_message(message_id, channel_id)
    response = f'Starting the offboarding process for "{first_name} {last_name}", using "{email}".'
    do_say(response, say)

    offboard(first_name, last_name, email, say)


def handle_offboarding_nevermind(body, say):
    """Triggers if the user changes their mind and elects not to proceed on the "are you sure" warning."""
    # Container section of the body has message ID and channel ID needed to delete the block we sent previously
    container = body["container"]
    channel_id = container["channel_id"]
    message_id = container["message_ts"]

    delete_slack_message(message_id, channel_id)
    response = "Okay :ok_hand: I wont offboard the user."
    do_say(response, say)
