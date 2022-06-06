"""Common function to obtain the required secrets from AWS secrets manager"""
import json
import boto3


def get_secret() -> dict:
    """Retrieves the various keys from AWS secrets manager"""
    secret_name = "*****************"
    region_name = "*****************"

    session = boto3.session.Session()
    client = session.client(service_name="secretsmanager", region_name=region_name)

    get_secret_value_response = client.get_secret_value(SecretId=secret_name)
    secret = get_secret_value_response["SecretString"]
    return json.loads(secret)
