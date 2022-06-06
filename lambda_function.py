"""**** AutoBot"""
import requests
import scripts.telq
import scripts.onboarding
import scripts.smsprimary
from scripts.get_secret import get_secret
from slack_bolt import App
from slack_bolt.adapter.aws_lambda import SlackRequestHandler

# Need to have secrets available before any other execution happens.
secrets = get_secret()


def respond_to_slack_within_3_seconds(ack: object) -> None:
    """Responds to Slack within the 3 second requirement"""
    ack()


def index_in_list(a_list: list, index: int) -> bool:
    """Verifies if a given index exists in a list"""
    return index < len(a_list)


def do_say(thing: str, say: object) -> None:
    """Does a "say" to slack while printing that say to the logs"""
    print(f"Doing say: {thing}")
    say_response = say(thing)
    return say_response


def check_user_is_noc(user: str) -> bool:
    """Check if user invoking tool is a member of the @nocteam usergroup (*****************) in slack"""
    header_data = {"Authorization": f"Bearer {secrets['token']}"}
    payload = {"usergroup": "*****************"}
    response = requests.get(
        "https://slack.com/api/usergroups.users.list", headers=header_data, params=payload
    ).json()
    user_list = response["users"]
    if user in user_list:
        print("User appears to be in the @nocteam")
        return True
    print("User is NOT in the @nocteam")
    return False


def handle_app_mentions(body: object, say: object) -> None:
    """Processes @ mentions to the bot. Here we parse the body for the invoking user and keywords/arguments used.
    Most of the code for subsequent functions exists in the scripts folder"""
    user_id = body["event"]["user"]
    text = body["event"]["text"]
    channel = body["event"]["channel"]
    options = text.split()

    print(f"Received text: {text}")
    print(f"Received @ mention from {user_id}")
    print(f"Received from channel {channel}")

    noc_user_bool = check_user_is_noc(user_id)
    valid_keywords = ["Help", "Test", "Rollout", "Update", "Primary", "TelQ", "Onboard", "Offboard"]

    noc_only_response = f"Sorry <@{user_id}>! Only members of the CloudOps team can use this function! Please contact CloudOps for assistance."
    main_help_message = f"Hello <@{user_id}>! I am 'AutoBot', the Ops Utility Bot. :robot_face:\nI can help with several functions. To use, tag me again followed by one of the following keywords:\n• Test - Send SMS, Voice and Email test notifications (and test confirmation functionality).\n• Rollout - Fire all possible path tests to yourself at once.\n• Update - Update *** contact information from Slack.\n• Primary - Check current primary/secondary SMS providers.\n• Telq - Send SMS tests to TelQ test endpoints (CloudOps use Only).\n• Primary switch - Switch primary/secondary SMS providers (CloudOps use Only).\n• Onboard - Onboard a member of SaaSOps (CloudOps use Only).\n• Offboard - Offboard a member of SaaSOps (CloudOps use Only).\n• Help - Print this help message.\n\nYou can also get additional help by invoking any keyword followed by 'help' for more details.\n\n<*****************|Click here to see the documentation.>"
    test_help_message = "The \"test\" keyword is used for testing SMS, Voice and Email notifications from *** and to test confirmations.\nTo use, simply tag me and use the \"test\" keyword followed by one or more of the following notification paths: [*SMS*, *Email*, *Voice*].\nOptionally, you can also specify one or both production stacks to send these notifications from: [*US*, *EU*].\n\t• If no stack is specified, defaults to 'US'.\nAdditionally, you can tag one or more other Slack users and they will be included in your tests. It is not possible to exclude yourself.\n\nIf you confirm a received notification I will report to you any confirmations that *** tells me about.\n\nHere are some examples:\nSend an SMS test from the US stack: `@AutoBot test sms`\nSend Voice test from the EU stack: `@AutoBot test voice eu`\nSend sms and voice from both stacks, including additional users: `@AutoBot test sms voice us eu @otherguy1 @otherguy2`\n\nBesides the 'test' keyword, the order of these options does not matter, nor does capitalization."
    rollout_help_message = "The 'rollout' keyword fires off all possible test notifications at once: SMS, Voice and Email from both US and EU stacks.\nTo use, simply tag me and use the 'rollout' keyword. No additional arguments are accepted.\n\nExample: `@AutoBot rollout`"
    update_help_message = "Kicks off an update of the associated contact info for the specified users in *** to match what is currently in their Slack profiles.\n\nAfter the 'update' keyword you may tag any number of Slack users and their *** contact profiles will be synchronized with their current Slack profile data. If no additional arguments are specified, only the contact information of the invoker is updated.\n\nOf note is that this system tries to determine which country your phone number belongs to via your slack timezone settings. Currently we only support India and US numbers. If your timezone is not set to India, you can include +91 at the start of your phone number and the system will detect this. It is not currently possible to force a US number or any other country for that matter. Number formatting should not otherwise be relevant.\n\nThis process can sometimes take a while, but you should get a useful report of any errors encountered during the process so be patient and give it at least 10 minutes before you assume it didn't work.\n\nExample updating your own contact data only: `@AutoBot update`\nExample updating two other Slack members contact data: `@AutoBot update @otherguy1 @otherguy2`"
    telq_help_message = "(CloudOps use Only)\nThe 'TelQ' keyword is used to send test SMS messages to various SIM devices around the world using the TelQ service.\nThis keyword requires the following format: `@AutoBot telq STACK COUNTRY_CODE`\n\nWhere *STACK* is one of the following *** stacks: [*US*, *EU*, *STG*]\nWhere *COUNTRY_CODE* is the official two digit country code for the country you wish to test to. <https://www.iban.com/country-codes|See this page for an official list of country codes.>\n\nUnlike the 'test' keyword, additional arguments must be in the correct order, although capitalization still does not matter.\n\nOnce invoked, you will be presented a list of all available test networks/carriers for that country, if any, to choose from. Simply select one or more from this list and submit. The tests will then be queued up on the TelQ service and notifications will be sent from the *** stack you selected.\nTest results must be obtained from <https://app.telqtele.com/#/manual-testing|the TelQ w***ite.>\n\nHere are some Examples:\nSend test to the United States from the US production stack: `@AutoBot telq US US`\nSend test to the UK from the EU stack: `@AutoBot telq EU GB`\nSend test to India from the Stage stack: `@AutoBot telq stg in`"
    onboard_help_message = "(CloudOps use Only)\nThe 'onboard' keyword allows a member of the CloudOps team to quickly onboard a new member of SaaSOps or anyone who needs access to SaaSOps tools. To use, simply tag me with the keyword 'onboard' followed by the new users first name and last name. You can optionally provide an email address as a third argument if the users email does not follow the first.last@*****************.com format exactly. Otherwise, the email will be auto computed from the users names.\n\nExample: `@AutoBot onboard john smith`\n\nWe currently support automated onboarding for the following tools/services:\nAlertsite, Datadog, SumoLogic.\n\nThe order of arguments/options does matter, but capitalization does not.\n\nOf note, by default this tool only provides basic access roles aka, 'read-only' type access. Elevated permissions must be manually configured."
    offboard_help_message = "(CloudOps use Only)\nThe 'offboard' keyword allows a member of the CloudOps team to quickly offboard a user from SaaSOps tools. To use, simply tag me with the keyword 'offboard' followed by the users first name and last name. You can optionally provide an email address as a third argument if the users email does not follow the first.last@*****************.com format exactly. Otherwise, the email will be auto computed from the users names.\n\nExample: `@AutoBot offboard john smith`\n\nWe currently support automated offboarding for the following tools/services:\nAlertsite, Datadog, SumoLogic.\n\nCapitalization does not matter."
    primary_help_message = "The 'primary' keyword allows a user to quickly determine the primary and secondary SMS service providers in any given production stack for any given country.\nThis keyword requires the following format: `@AutoBot primary STACK COUNTRY_CODE`\n\nWhere *STACK* is one of the following *** stacks: [*US*, *EU*]\nWhere *COUNTRY_CODE* is the official two digit country code for the country you wish to look up. <https://www.iban.com/country-codes|See this page for an official list of country codes.>\n\n*Switching Primary/Secondary*\n(CloudOps use Only) You can optionally pass the word \"switch\" as your second argument and the primary and secondary will be switched in the DB. This still requires the SMS connectors to be manually restarted to pickup these changes. This functionality still requires you to specify the stack and 2 letter country code after the word switch.\n\nAll arguments must be in the correct order, although capitalization does not matter.\n\nHere are some Examples:\nCheck primary for United States on the US production stack: `@AutoBot primary US US`\nCheck primary for the UK from the EU stack: `@AutoBot primary EU GB`\nSwitch primary/secondary for India from the EU stack: `@AutoBot primary switch us in`"

    print(f"Detected options: {options}")
    if index_in_list(options, 1) is False:  # Happens if no keywords are used at all.
        key_words = ", ".join(valid_keywords)
        response = f"Sorry <@{user_id}>! You must include one of the following keywords as your first argument:\n{key_words}"
        do_say(response, say)
        return
    # If the bot is tagged but not first we have to do something with that. If this is annoying we might just silently discard the event.
    elif options[0] != "<@*****************":
        response = f"Hey <@{user_id}>! You seem to have tagged me in a message but not as the first word/thing. In case you need me to do something, you'll need to tag me as the very first thing. Try `@AutoBot help` for help."
        do_say(response, say)
        return
    # Easter Egg
    elif options[1].casefold() == "jes":
        response = "mmjes"
        do_say(response, say)
        return

    elif options[1].casefold() == "help":
        do_say(main_help_message, say)
        return
    # rollout triggers all three tests in both envs
    elif options[1].casefold() == "rollout":
        if index_in_list(options, 2) is True:
            if options[2].casefold() == "help":
                do_say(rollout_help_message, say)
                return
        from scripts.pathtest import path_test

        rollout_options = ["<@*****************>", "test", "sms", "voice", "email", "us", "eu"]
        path_test(rollout_options, user_id, channel, say)
        return
    # "test" keyword means we want to send test notifications.
    elif options[1].casefold() == "test":
        if index_in_list(options, 2) is True:
            if options[2].casefold() == "help":
                do_say(test_help_message, say)
                return
        from scripts.pathtest import path_test

        path_test(options, user_id, channel, say)
        return

    elif options[1].casefold() == "update":
        if index_in_list(options, 2) is True:
            if options[2].casefold() == "help":
                do_say(update_help_message, say)
                return
        response = "Kicking off a contact update! Please note that this process can take up to 60 seconds per contact."
        do_say(response, say)
        from scripts import contact

        update_contacts_response = contact.handler(options, user_id)
        if update_contacts_response["ok"] is True:
            response = f"Contacts have been updated in *** and no errors have been detected! :data_party:\n\nI have successfully updated the following contacts:\n{', '.join(update_contacts_response['users'])}."
            do_say(response, say)
        else:
            new_line = "\n"  # Ugh. No backslashes allowed in f string brackets so we do this...
            response = f"There has been some error during the contact update process :cry:\nWe failed at the following step(s):\n{new_line.join(update_contacts_response['step'])}\n\nHere are the corresponding error message(s) encountered:\n{new_line.join(update_contacts_response['errors'])}\n\n"
            if update_contacts_response["users"]:
                addendum = f"I have successfully updated the following contacts:\n{', '.join(update_contacts_response['users'])}.\n<*****************|See the documentation for common errors and how to resolve them.>"
            else:
                addendum = "I do not seem to have updated any users in ***.\n<*****************|See the documentation for common errors and how to resolve them.>"
            response = response + addendum
            do_say(response, say)

    elif options[1].casefold() == "telq":  # Telq starts here
        if index_in_list(options, 2) is True:
            if options[2].casefold() == "help":
                do_say(telq_help_message, say)
                return
        if noc_user_bool is False:  # Keyword is locked to CloudOps only for now
            do_say(noc_only_response, say)
            return

        if index_in_list(options, 3) is False or index_in_list(options, 4) is True:
            response = f"Sorry <@{user_id}>, the TelQ tool takes *exactly 2* arguments:\n1) An *** Production stack: [*US*, *EU*, *STG*] to send from.\n2) A 2 letter country code. \n\nExample: `@AutoBot telq US IN`\nTry `@AutoBot telq help` for help."
            do_say(response, say)
            return
        elif len(options[3]) != 2:
            response = f"Sorry <@{user_id}>, you can only enter *2* letters for your country code. Example: `@AutoBot telq US IN`\nTry `@AutoBot telq help` for help."
            do_say(response, say)
            return
        elif options[2].casefold() not in ["us", "eu", "stg"]:
            response = f"Sorry <@{user_id}>, You must use one of the following for your choice of *** Production stack: [*US*, *EU*, *STG*]. Example: `@AutoBot telq US IN`\nTry `@AutoBot telq help` for help."
            do_say(response, say)
            return
        scripts.telq.handle_network_selection(options, say)

    elif options[1].casefold() == "onboard":  # Onboarding starts here
        if noc_user_bool is False:  # Keyword is locked to CloudOps only for now
            do_say(noc_only_response, say)
            return
        if index_in_list(options, 2) is True:
            if options[2].casefold() == "help":
                do_say(onboard_help_message, say)
                return
        scripts.onboarding.onboard(options, user_id, say)

    elif options[1].casefold() == "offboard":  # Offboarding starts here
        if noc_user_bool is False:  # Keyword is locked to CloudOps only for now
            do_say(noc_only_response, say)
            return
        if index_in_list(options, 2) is True:
            if options[2].casefold() == "help":
                do_say(offboard_help_message, say)
                return
        scripts.onboarding.kickoff_offboard(options, user_id, say)

    elif options[1].casefold() == "primary":  # SMS Primary starts here
        if index_in_list(options, 2) is True:
            if options[2].casefold() == "help":
                do_say(primary_help_message, say)
                return
            elif options[2].casefold() == "switch":
                if noc_user_bool is False:  # Keyword is locked to CloudOps only for now
                    do_say(noc_only_response, say)
                    return
                scripts.smsprimary.switch_sms_primary(options, user_id, say)
                return
        scripts.smsprimary.sms_route_check(options, user_id, say)

    else:  # No recognized keyword used
        key_words = ", ".join(valid_keywords)
        response = f"Sorry <@{user_id}>! You must include one of the following keywords as your first argument:\n{key_words}"
        do_say(response, say)


# "Lazy" mode allows further processing after initial Ack to slack.
app = App(
    signing_secret=secrets["signing_secret"], token=secrets["token"], process_before_response=True
)
app.event("app_mention")(
    ack=respond_to_slack_within_3_seconds, lazy=[handle_app_mentions]
)

# This basically does nothing but is needed to avoid 404 errors for the end user
app.action("network_select_action")(
    ack=respond_to_slack_within_3_seconds, lazy=[scripts.telq.handle_network_select_action]
)

# Handles what happens when a user submits a list of networks to test to via TelQ
app.action("submit_networks")(
    ack=respond_to_slack_within_3_seconds, lazy=[scripts.telq.handle_submit_networks]
)

# Handles what happens when a user says they are sure about offboarding
app.action("offboard_request")(
    ack=respond_to_slack_within_3_seconds, lazy=[scripts.onboarding.handle_offboarding]
)

# Handles what happens when a user changes their mind about offboarding someone
app.action("offboard_nevermind")(
    ack=respond_to_slack_within_3_seconds, lazy=[scripts.onboarding.handle_offboarding_nevermind]
)

# Handles what happens when a user says they are sure about switching SMS
app.action("switch_primary_sms")(
    ack=respond_to_slack_within_3_seconds, lazy=[scripts.smsprimary.handle_primary_switch]
)

# Handles what happens when a user changes their mind about offboarding someone
app.action("switch_primary_sms_nevermind")(
    ack=respond_to_slack_within_3_seconds, lazy=[scripts.smsprimary.handle_primary_switch_nevermind]
)


def handler(event, context):
    """Handler for AWS lambda"""
    slack_handler = SlackRequestHandler(app=app)
    return slack_handler.handle(event, context)
