"""Lambda handler file to receive response subscriptions from ***"""
import json
import boto3
from scripts.get_secret import get_secret  # pylint: disable=import-error
from slack_sdk import WebClient

# Need to have secrets available before any other execution happens.
secrets = get_secret()


def lookup_db_info(ebid: int) -> str:
    """Takes an EB incident ID and looks up the associated row in the dynamoDB"""
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table("*****************")
    response = table.get_item(Key={"id": ebid})
    return response


def main(event, context):
    """Response Subscription Lambda Handler"""
    print(f"Received event:\n{event}")
    print(f"Received context:\n{context}")
    body = json.loads(event["body"])

    try:
        incident_id = body["id"]
        org_id = body["organizationId"]
        print("Incident ID Detected: ", incident_id)
        print("org_id Detected: ", org_id)
    except:
        print("Event doesn't appear to be a confirmation")
        return

    try:
        delivery_method = body["name"]
        print("deliveryMethod Detected: ", delivery_method)
    except:
        print("Could not determine delivery_method")
        return

    try:
        db_info = lookup_db_info(incident_id)
    except:
        print("Failed to find DB entry. Maybe an old confirmation?")
        return

    try:
        slack_channel = db_info["Item"]["channel_id"]
        results_url = db_info["Item"]["delivery_url"]
        print("Found Slack Channel ID: ", slack_channel)
        print("Found Results URL: ", results_url)
    except:
        print("Unable to locate slack channel or results_url from DB results")
        return

    user_list = []
    for index in range(len(body["responses"])):
        try:
            user_list.append(body["responses"][index]["externalId"])
            print("Slack User ID Detected: ", body["responses"][index]["externalId"])
        except:
            print("Couldn't locate a User ID")
            return

    stack = "US" if str(org_id) == "*****************" else "EU"
    client = WebClient(token=secrets["token"])
    if len(user_list) == 1:
        message = f"Received {delivery_method} confirmation response from <@{user_list[0]}> on {stack} stack! :meowparty:"
    else:
        message = f"Received {delivery_method} confirmation response from the following users on {stack} stack:\n{', '.join(['<@'+user+'>' for user in user_list])} :meowparty:"

    _ = client.chat_postMessage(channel=slack_channel, text=message)
