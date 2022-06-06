"""Module for TelQ SMS Testing"""
import time
import requests
from scripts.get_secret import get_secret  # pylint: disable=import-error

# Need to have secrets available before any other execution happens.
secrets = get_secret()


def do_say(thing: str, say: object) -> None:
    """Does a "say" to slack while printing that say to the logs"""
    print(f"Doing say: {thing}")
    say_response = say(thing)
    return say_response


def delete_slack_message(message_id, channel_id):
    """Deletes a slack message for situations in which
    we have no response URL and cannot override previous messages"""
    url = "https://slack.com/api/chat.delete"
    headers = {"authorization": f"Bearer {secrets['token']}"}
    payload = {"channel": f"{channel_id}", "ts": f"{message_id}"}
    response = requests.post(url, json=payload, headers=headers)
    output = response.json()
    return output


def obtain_bearer_token() -> dict:
    """Takes an app_id and appKey value input.
    Obtained from TelQ UI on a per-user level.
    Outputs a bearer token which is required for all future API calls"""
    url = "https://api.telqtele.com/v2/client/token"
    payload = {"appId": secrets["app_id"], "appKey": secrets["app_key"]}
    response = requests.post(url, json=payload)
    output = response.json()["value"]
    return output


def get_networks(token) -> dict:
    """Downloads entire list of available networks"""
    auth_header = {"authorization": token}
    url = "https://api.telqtele.com/v2/client/networks"
    response = requests.get(url, headers=auth_header)
    return response.json()


def get_country_networks(country_name: str, networks: dict) -> list:
    """Return a list of non-ported network/test targets for a specific country.
    We do not currently test to ported numbers."""
    result_list = []
    for net in networks:
        if net["countryName"] == country_name:
            if net["portedFromMnc"] is None:
                result_list.append(net)
    return result_list


def set_env_vars(env: str) -> dict:
    """Set various environment variables depending on the
    selected *** environment we want to test from"""
    if env.casefold() == "us":
        env_vars = {
            "name": "Prod US",
            "apiKey": secrets["us_***_api_key"],
            "orgId": "*****************",
            "recordTypeId": "*****************",
            "accountId": "*****************",
            "deliveryId": "*****************",
            "endpoint": "https://api.*****************.net",
        }
    elif env.casefold() == "eu":
        env_vars = {
            "name": "Prod EU",
            "apiKey": secrets["eu_***_api_key"],
            "orgId": "*****************",
            "recordTypeId": "*****************",
            "accountId": "*****************",
            "deliveryId": "*****************",
            "endpoint": "https://api.*****************.eu",
        }
    elif env.casefold() == "stg":
        env_vars = {
            "name": "Stage",
            "apiKey": secrets["stg_***_api_key"],
            "orgId": "*****************",
            "recordTypeId": "*****************",
            "accountId": "*****************",
            "deliveryId": "*****************",
            "endpoint": "https://api-stage.*****************.net",
        }
    return env_vars


def create_test(token: str, mcc: str, mnc: str) -> dict:
    """Tells the TelQ system that we'd like to test a specific network.
    Outputs the first value in the response which contains
    the test id, 'testIdText' and destination phoneNumber."""
    auth_header = {"authorization": token}
    data = {"destinationNetworks": [{"mcc": mcc, "mnc": mnc}]}
    response = requests.post(
        "https://api.telqtele.com/v2/client/tests", headers=auth_header, json=data
    )
    output = response.json()
    print(f"Received response from TelQ during create test: {output}")
    return output


def create_contact(stack, country_code, phone_number) -> str:
    """Create a contact in the TelQ org in *** with the information provided from telq."""
    environment = set_env_vars(stack)
    contact_data = {
        "organizationId": environment["orgId"],
        "lastName": phone_number,
        "status": "A",
        "country": country_code.upper(),
        "recordTypeId": environment["recordTypeId"],
        "accountId": "0",
        "externalId": phone_number,
        "paths": [
            {
                "waitTime": "0",
                "pathId": "*****************",
                "countryCode": country_code.upper(),
                "value": phone_number,
                "skipValidation": "false",
            }
        ],
        "firstName": "TelQ Test",
        "timezoneId": "America/New_York",
    }
    header_data = {"Authorization": environment["apiKey"]}
    api_endpoint = str(environment["endpoint"]) + "/rest/contacts/" + environment["orgId"]
    response = requests.post(api_endpoint, headers=header_data, json=contact_data)
    print(f"Received following response from *** when creating contact:\n{response.json()}")
    return response.json()


def delete_contact(stack, contact_id) -> str:
    """Deletes contact from ***"""
    environment = set_env_vars(stack)
    api_endpoint = (
        f"{environment['endpoint']}/rest/contacts/{environment['orgId']}/{contact_id}?idType=id"
    )
    header_data = {"Authorization": environment["apiKey"]}
    response = requests.delete(api_endpoint, headers=header_data)
    print(f"Received following response from *** when deleting contact:\n{response.json()}")
    return response.json()


def send_notification(stack, country_code, test_id_text, contact_id) -> str:
    """Sends a notification to given contact ID"""
    environment = set_env_vars(stack)
    message_body = " You may have to leave your home quickly to stay safe."
    title = country_code + " Short Auto Message (AutoBot)"
    notification_data = {
        "status": "A",
        "priority": "NonPriority",
        "type": "Standard",
        "message": {
            "contentType": "Text",
            "title": title,
            "textMessage": test_id_text + message_body,
        },
        "broadcastContacts": {"contactIds": [contact_id]},
        "broadcastSettings": {
            "confirm": "false",
            "deliverPaths": [
                {
                    "accountId": environment["accountId"],
                    "pathId": "*****************",
                    "organizationId": environment["orgId"],
                    "id": environment["deliveryId"],
                    "status": "A",
                    "seq": 1,
                    "prompt": "SMS",
                    "extRequired": "false",
                    "displayFlag": "false",
                    "default": "false",
                }
            ],
        },
        "launchtype": "SendNow",
    }
    header_data = {"Authorization": environment["apiKey"]}
    api_endpoint = str(environment["endpoint"]) + "/rest/notifications/" + environment["orgId"]
    response = requests.post(api_endpoint, headers=header_data, json=notification_data)
    notification_response = response.json()
    print(
        f"Received following response from *** when sending notification:\n{notification_response}"
    )
    return notification_response


def find_country_name(c_code):
    """Takes 2 letting country code and returns TelQ matching country name
    Previously we used pycountry but the names there don't always correspond
    to the spellings in TelQ, so we manually created this. It's possible if
    a name is changed in TelQ someone will need to manually add/fix it here."""
    country_map = {
        "AD": "Andorra",
        "AE": "United Arab Emirates",
        "AF": "Afghanistan",
        "AG": "Antigua and Barbuda",
        "AI": "Anguilla",
        "AL": "Albania",
        "AM": "Armenia",
        "AO": "Angola",
        "AQ": "Antarctica",
        "AR": "Argentina",
        "AS": "Samoa",
        "AT": "Austria",
        "AU": "Australia",
        "AW": "Aruba",
        "AX": "Aland",
        "AZ": "Azerbaijan",
        "BA": "Bosnia and Herzegovina",
        "BB": "Barbados",
        "BD": "Bangladesh",
        "BE": "Belgium",
        "BF": "Burkina Faso",
        "BG": "Bulgaria",
        "BH": "Bahrain",
        "BI": "Burundi",
        "BJ": "Benin",
        "BL": "Saint Barthelemy",
        "BM": "Bermuda",
        "BN": "Brunei",
        "BO": "Bolivia",
        "BQ": "Bonaire",
        "BR": "Brazil",
        "BS": "Bahamas",
        "BT": "Bhutan",
        "BV": "Bouvet",
        "BW": "Botswana",
        "BY": "Belarus",
        "BZ": "Belize",
        "CA": "Canada",
        "CC": "Cocos",
        "CD": "DR Congo",
        "CF": "Central",
        "CG": "Congo",
        "CH": "Switzerland",
        "CI": "Cote",
        "CK": "Cook Islands",
        "CL": "Chile",
        "CM": "Cameroon",
        "CN": "China",
        "CO": "Colombia",
        "CR": "Costa Rica",
        "CU": "Cuba",
        "CV": "Cape Verde",
        "CW": "Curacao and the Caribbean Netherlands",
        "CX": "Christmas Island",
        "CY": "Cyprus",
        "CZ": "Czech Republic",
        "DE": "Germany",
        "DJ": "Djibouti",
        "DK": "Denmark",
        "DM": "Dominica",
        "DO": "Dominican Republic",
        "DZ": "Algeria",
        "EC": "Ecuador",
        "EE": "Estonia",
        "EG": "Egypt",
        "EH": "Western Sahara",
        "ER": "Eritrea",
        "ES": "Spain",
        "ET": "Ethiopia",
        "FI": "Finland",
        "FJ": "Fiji",
        "FK": "Falkland Islands",
        "FM": "Micronesia",
        "FO": "Faroe Islands",
        "FR": "France",
        "GA": "Gabon",
        "GB": "United Kingdom",
        "GD": "Grenada",
        "GE": "Georgia",
        "GF": "Guadeloupe, Martinique and French Guiana",
        "GG": "Guernsey",
        "GH": "Ghana",
        "GI": "Gibraltar",
        "GL": "Greenland",
        "GM": "Gambia",
        "GN": "Guinea",
        "GP": "Guadeloupe",
        "GQ": "Equatorial",
        "GR": "Greece",
        "GS": "South",
        "GT": "Guatemala",
        "GU": "Guam",
        "GW": "Guinea",
        "GY": "Guyana",
        "HK": "Hong Kong",
        "HM": "Heard and McDonald Islands",
        "HN": "Honduras",
        "HR": "Croatia",
        "HT": "Haiti",
        "HU": "Hungary",
        "ID": "Indonesia",
        "IE": "Ireland",
        "IL": "Israel",
        "IM": "Isle of Man",
        "IN": "India",
        "IO": "British Indian Ocean",
        "IQ": "Iraq",
        "IR": "Iran",
        "IS": "Iceland",
        "IT": "Italy",
        "JE": "Jersey",
        "JM": "Jamaica",
        "JO": "Jordan",
        "JP": "Japan",
        "KE": "Kenya",
        "KG": "Kyrgyzstan",
        "KH": "Cambodia",
        "KI": "Kiribati",
        "KM": "Comoros",
        "KN": "Saint Kitts and Nevis",
        "KP": "North Korea",
        "KR": "South Korea",
        "KW": "Kuwait",
        "KY": "Cayman Islands",
        "KZ": "Kazakhstan",
        "LA": "Laos",
        "LB": "Lebanon",
        "LC": "Saint Lucia ",
        "LI": "Liechtenstein",
        "LK": "Sri Lanka",
        "LR": "Liberia",
        "LS": "Lesotho",
        "LT": "Lithuania",
        "LU": "Luxembourg",
        "LV": "Latvia",
        "LY": "Libya",
        "MA": "Morocco",
        "MC": "Monaco",
        "MD": "Moldova",
        "ME": "Montenegro",
        "MF": "Saint Martin",
        "MG": "Madagascar",
        "MH": "Marshall Islands",
        "MK": "North Macedonia",
        "ML": "Mali",
        "MM": "Myanmar",
        "MN": "Mongolia",
        "MO": "Macau",
        "MP": "Northern Mariana Islands",
        "MQ": "Guadeloupe, Martinique and French Guiana",
        "MR": "Mauritania",
        "MS": "Montserrat",
        "MT": "Malta",
        "MU": "Mauritius",
        "MV": "Maldives",
        "MW": "Malawi",
        "MX": "Mexico",
        "MY": "Malaysia",
        "MZ": "Mozambique",
        "NA": "Namibia",
        "NC": "New Caledonia",
        "NE": "Niger",
        "NF": "Norfolk Island",
        "NG": "Nigeria",
        "NI": "Nicaragua",
        "NL": "Netherlands",
        "NO": "Norway",
        "NP": "Nepal",
        "NR": "Nauru",
        "NU": "Niue",
        "NZ": "New Zealand",
        "OM": "Oman",
        "PA": "Panama",
        "PE": "Peru",
        "PF": "French Polynesia",
        "PG": "Papua New Guinea",
        "PH": "Philippines",
        "PK": "Pakistan",
        "PL": "Poland",
        "PM": "Saint Pierre and Miquelon",
        "PN": "Pitcairn Islands",
        "PR": "Puerto Rico",
        "PS": "Palestine",
        "PT": "Portugal",
        "PW": "Palau",
        "PY": "Paraguay",
        "QA": "Qatar",
        "RE": "Reunion and Mayotte",
        "RO": "Romania",
        "RS": "Serbia",
        "RU": "Russian Federation",
        "RW": "Rwanda",
        "SA": "Saudi Arabia",
        "SB": "Solomon Islands",
        "SC": "Seychelles",
        "SD": "Sudan",
        "SE": "Sweden",
        "SG": "Singapore",
        "SH": "Saint Helena, Ascension and Tristan da Cunha",
        "SI": "Slovenia",
        "SJ": "Svalbard and Jan Mayen",
        "SK": "Slovakia",
        "SL": "Sierra Leone",
        "SM": "San Marino",
        "SN": "Senegal",
        "SO": "Somalia",
        "SR": "Suriname",
        "SS": "South Sudan",
        "ST": "Sao Tome and Principe",
        "SV": "El Salvador",
        "SX": "Sint Maarten",
        "SY": "Syria",
        "SZ": "Swaziland",
        "TC": "Turks and Caicos Islands",
        "TD": "Chad",
        "TF": "French Southern and Antarctic Lands",
        "TG": "Togo",
        "TH": "Thailand",
        "TJ": "Tajikistan",
        "TK": "Tokelau",
        "TL": "Timor-Leste",
        "TM": "Turkmenistan",
        "TN": "Tunisia",
        "TO": "Tonga",
        "TR": "Turkey",
        "TT": "Trinidad and Tobago",
        "TV": "Tuvalu",
        "TW": "Taiwan",
        "TZ": "Tanzania",
        "UA": "Ukraine",
        "UG": "Uganda",
        "UM": "United States Minor Outlying Islands",
        "US": "United States of America",
        "UY": "Uruguay",
        "UZ": "Uzbekistan",
        "VA": "Vatican City",
        "VC": "Saint Vincent and the Grenadines",
        "VE": "Venezuela",
        "VG": "British Virgin Islands",
        "VI": "US Virgin Islands",
        "VN": "Vietnam",
        "VU": "Vanuatu",
        "WF": "Wallis and Futuna",
        "WS": "Samoa",
        "YE": "Yemen",
        "YT": "Reunion and Mayotte",
        "ZA": "South Africa",
        "ZM": "Zambia",
        "ZW": "Zimbabwe",
    }
    return country_map[c_code.upper()]


def network_options_check(data: dict) -> list:
    """Determines specified options from the submitted form,
    outputs those options, the stack and the country code"""
    values = data["state"]["values"]
    stack = data["actions"][0]["value"]
    block_id = next(iter(values.keys()))  # This value is unique to each interaction
    selected_options = values[block_id]["network_select_action"]["selected_options"]
    network_list = []
    for opt in selected_options:
        print(f"Received Network Info: {opt}")
        network_info = {}
        network_info["carrier"] = opt["text"]["text"]
        network_info["mcc"] = opt["value"][0:3]
        network_info["mnc"] = opt["value"][3:]
        print(f"Detected Network Choice: {network_info}")
        network_list.append(network_info)

    header_block_text = data["message"]["blocks"][0]["text"]["text"]  # Yuk ¯\_(ツ)_/¯
    header_block_split = header_block_text.split()
    country_code = header_block_split[2]

    return [network_list, stack, country_code]


def handle_network_select_action():
    """We seem to need some function to pass to avoid displaying 404 errors when selecting networks"""
    return


def handle_submit_networks(body, respond, say):
    """Once the network list form is submitted, create telq test,
    create contact, send notification, delete contact"""
    network_data = network_options_check(body)
    network_list = network_data[0]
    stack = network_data[1]
    country_code = network_data[2]
    country_name = find_country_name(country_code)
    carrier_list = [carrier["carrier"] for carrier in network_list]
    response = (
        f"Sending SMS tests from the {stack} stack to the following carriers in {country_name}:\n"
    )
    for carrier in carrier_list:
        response += f"{carrier}, "
    response = response.rstrip(", ")  # Strip the last comma and space
    response += ".\n\nThis make take up to 10 seconds per test."
    respond(text=response, delete_original=True, response_type="in_channel")
    telq_token = obtain_bearer_token()
    contact_error = False
    contact_results = []
    contact_ids = []
    for network in network_list:
        try:
            telq_test = create_test(telq_token, network["mcc"], network["mnc"])
            test_data = telq_test[0]
        except:
            response = f"There has been an error creating a test in TelQ. Here is the response received:\n{telq_test}\n\nThis error is fatal. Giving up."
            do_say(response, say)
            return
        try:
            create_contact_response = create_contact(stack, country_code, test_data["phoneNumber"])
            contact_id = create_contact_response["id"]
            contact_ids.append(contact_id)
        except:
            response = f"There has been an error creating the contact in ***. Here is the response received:\n{create_contact_response}\n\nThis error is fatal. Giving up."
            do_say(response, say)
            return
        try:
            notification_response = send_notification(
                stack, country_code, test_data["testIdText"], contact_id
            )
            notification_id = notification_response["id"]
            print(f"Successfully sent notification: {notification_id}")
        except:
            response = f"There has been an error sending the notification in ***. Here is the response received:\n{notification_response}\n\nThis error is fatal. Giving up."
            do_say(response, say)
            return notification_response

    response = "All tests successfully sent from ***! :data_party:\n\nCheck TelQ for results:\nhttps://app.telqtele.com/#/manual-testing"
    respond(text=response, delete_original=True, response_type="in_channel", unfurl_links=False)
    # Wait 15 seconds after triggering notifications to ensure 
    # that contact is not deleted before notification is initiated.
    # It's possible this may need to be increased but this already 
    # dramatically increases function time so careful balance is needed.
    time.sleep(15)
    print("Starting contact delete")
    for contact in contact_ids:
        time.sleep(2)  # 2 second delay keeps *** API from rate limiting us (hopefully)
        try:
            delete_contact_response = delete_contact(stack, contact)
            if delete_contact_response["message"].casefold() != "ok":
                contact_error = True
                contact_results.append(delete_contact_response)
        except:
            contact_error = True
            contact_results.append(delete_contact_response)
    if contact_error is True:
        newline = "\n"
        respond(
            f"While trying to delete the *** contact(s) we created for this test, we encountered one or more errors:\n{newline.join(contact_results)}\n\nThis does not affect the test, but you might want to manually clean up these contacts."
        )


def handle_network_selection(options, say):
    """Takes user input, parses options, queries telq for available test networks,
    sends that information in block form to the user."""
    say_response = do_say(
        "Obtaining list of available test networks from TelQ. This may take up to 60 seconds.", say
    )
    channel_id = say_response["channel"]
    message_id = say_response["ts"]
    country_code = options[3].upper()
    try:
        country_name = find_country_name(country_code)
    except BaseException as err:
        print(err)
        do_say(
            f'I don\'t seem to be able to find a country using this country code: "{country_code}". Are you sure you\'ve entered an official code? The UK for example is actually "GB"!\n\n<https://www.iban.com/country-codes|See this page for an official list of country codes.>\n\nThis is a fatal error. Please try again.',
            say,
        )
        return
    stack = options[2].upper()

    telq_token = obtain_bearer_token()
    network_list = get_networks(telq_token)
    country_networks = get_country_networks(country_name, network_list)

    block_options = []
    for network in country_networks:
        list_item = {
            "text": {"type": "plain_text", "text": network["providerName"], "emoji": True},
            "value": network["mcc"] + network["mnc"],
        }
        block_options.append(list_item)
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{stack} Stack: {country_code} Network Selection",
                "emoji": True,
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Please select one or more Networks from the list below.",
            },
        },
        {"type": "divider"},
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "Select Networks:"},
            "accessory": {
                "type": "multi_static_select",
                "placeholder": {"type": "plain_text", "text": "Select Networks", "emoji": True},
                "options": block_options,
                "action_id": "network_select_action",
            },
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Submit", "emoji": True},
                    "value": stack,
                    "action_id": "submit_networks",
                }
            ],
        },
    ]
    delete_slack_message(message_id, channel_id)
    say(blocks=blocks)
