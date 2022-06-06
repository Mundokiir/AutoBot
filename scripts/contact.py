"""This script will scan and import contact data for users in Slack"""
import time
import requests
from scripts.get_secret import get_secret  # pylint: disable=import-error

# Need to have secrets available before any other execution happens.
secrets = get_secret()


def index_in_list(a_list: list, index: int) -> bool:
    """Verifies if a given index exists in a list"""
    return index < len(a_list)


def get_noc_users() -> dict:
    """Returns list of all users in the @nocteam group in slack"""
    # This function isn't currently in use and may need tweaking to re-enable
    header_data = {"Authorization": f"Bearer {secrets['token']}"}
    payload = {"usergroup": "*********"}
    tries = 3
    for i in range(tries):
        try:
            response = requests.get(
                "https://slack.com/api/usergroups.users.list",
                headers=header_data,
                params=payload,
                timeout=15,
            ).json()
        except BaseException as err:
            if i < tries:
                print(err)
                print("Trying again...")
                continue
            else:
                print("That's three tries. Giving up now.")
                response = {"ok": False, "error": err}
        break
    return response


def get_user_info(uid: str) -> dict:
    """Returns dict containing interested information about a slack user"""
    header_data = {"Authorization": f"Bearer {secrets['token']}"}
    payload = {"user": uid}
    tries = 3
    for i in range(tries):
        try:
            response = requests.get(
                "https://slack.com/api/users.info", headers=header_data, params=payload, timeout=15
            ).json()
        except BaseException as err:
            if i < tries:  # i is zero indexed
                print(err)
                print("Trying again...")
                continue
            else:
                print("That's three tries. Giving up now.")
                response = {"ok": False, "error": err}
        break
    if response["ok"] is True:
        profile = {}
        profile["ok"] = response["ok"]
        profile["phone"] = response["user"]["profile"]["phone"]
        profile["first_name"] = response["user"]["profile"]["first_name"]
        profile["last_name"] = response["user"]["profile"]["last_name"]
        profile["email"] = response["user"]["profile"]["email"]
        time_zone = response["user"]["tz_label"]
        # Some India CloudOps members elect to use PST. They can add +91 to the front of their number instead.
        if profile["phone"][0:3] == "+91":
            profile["tz"] = "IN"
            print("+91, setting CC to IN")
        elif "India" in time_zone:
            print("IST TZ, setting CC to IN")
            profile["tz"] = "IN"
        else:
            print("setting CC to US")
            profile["tz"] = "US"
        return profile
    return response


def create_contact(
    first: str, last: str, phone: str, email: str, org: str, extid: str, c_code: str
) -> dict:
    """Creates the contact in ***"""
    if org == "US":
        org_id = "*****************"
        api_endpoint = f"https://api.*****************.net/rest/contacts/{org_id}"
        path_id_voice = "*****************"
        path_id_sms = "*****************"
        path_id_email = "*****************"
        record_type = "*****************"
    if org == "EU":
        org_id = "*****************"
        api_endpoint = f"https://api.*****************.eu/rest/contacts/{org_id}"
        path_id_voice = "*****************"
        path_id_sms = "*****************"
        path_id_email = "*****************"
        record_type = "*****************"
    contact_data = {
        "organizationId": org_id,
        "firstName": first.title(),
        "lastName": last.title(),
        "status": "A",
        "country": c_code.upper(),
        "recordTypeId": record_type,
        "externalId": extid,
        "paths": [
            {
                "pathId": path_id_sms,
                "countryCode": c_code.upper(),
                "value": phone,
                "skipValidation": "false",
            },
            {
                "pathId": path_id_voice,
                "countryCode": c_code.upper(),
                "value": phone,
                "skipValidation": "false",
            },
            {"pathId": path_id_email, "value": email, "skipValidation": "false"},
        ],
    }
    header_data = {"Authorization": secrets["***_auth"]}
    tries = 3
    for i in range(tries):  # We need to retry because sometimes *** just decides to ignore us.
        try:
            response = requests.post(
                api_endpoint, headers=header_data, json=contact_data, timeout=15
            ).json()
        except BaseException as err:
            if i < tries:  # i is zero indexed
                print(err)
                print("Trying again...")
                continue
            else:
                print("That's three tries. Giving up now.")
                response = {}
                response["message"] = "Error"
                response["error"] = err
        break
    return response


def format_phone(number: str) -> str:
    """Strips non-numerical characters and returns the last 10 digits"""
    numerical = ""
    for character in number:
        if character.isdigit():
            numerical += character
    return numerical[-10:]


def handler(options, user_id):
    """Primary function handler"""
    final_result = {}
    errors = []
    fail_steps = []
    successful_users = []

    if index_in_list(options, 2) is True:
        # If user specified options we assume it's a list of names.
        user_list = []
        for opt in options:
            if opt == options[0] or opt == options[1] or opt[2:-1] in user_list:
                # 0 is the bot user, 1 is the "update" keyword. Also skip if this option is already in the list
                continue
            if opt[0] == "<" and opt[-1] == ">":
                user_list.append(opt[2:-1])
            else:  # User gave an option that is not a slack user
                errors.append(f'Option "{opt}" does not appear to be a properly tagged Slack user.')
        if errors:
            fail_steps.append("Parse User List")
    else:  # If no options specified, update the invokers profile instead
        user_list = [user_id]

    for user in user_list:
        # Helps keep *** from freaking out on us but does increase the time for this to run :(
        time.sleep(2)
        user_info = get_user_info(user)
        if user_info["ok"] is True:
            print(f"Successfully obtained {user} data from Slack")
            if user_info["phone"]:
                user_phone = format_phone(user_info["phone"])
            else:
                user_phone = "555"  # If no phone number, use a dummy number so we trigger an error
            for stack in ["US", "EU"]:
                print(
                    f"Sending the following data to ***:\nFN: {user_info['first_name']}, LN: {user_info['last_name']}, PN: {user_phone}, EM: {user_info['email']}, STACK: {stack}, UID: {user}, CC: {user_info['tz']}"
                )
                create_contact_response = create_contact(
                    user_info["first_name"],
                    user_info["last_name"],
                    user_phone,
                    user_info["email"],
                    stack,
                    user,
                    user_info["tz"],
                )
                if create_contact_response["message"] != "OK":
                    errors.append(str(create_contact_response))
                    fail_steps.append(f"Update *** Contact info for <@{user}> in {stack} stack")
                    print("Error updating *** contact:\n" + str(create_contact_response))
                    user_success = False
                else:
                    print(f"Successfully created Contact info for {user} in {stack} stack")
                    user_success = True
        else:
            errors.append(str(user_info))
            fail_steps.append("Obtain single user info from Slack")
            print("Error getting user data from slack:\n" + "\n".join(errors))
            break
        if user_success is True:
            successful_users.append(f"<@{user}>")  # Slack formatted

    if errors:
        print("Errors")
        success = False
    else:
        print("No Errors")
        success = True

    final_result["ok"] = success
    final_result["errors"] = errors
    final_result["step"] = fail_steps
    final_result["users"] = successful_users
    return final_result
