"""Module to handle on and offboarding of users in DataDog."""
import requests


class DataDogOnBoarder:
    """Class to handle on and offboarding of users in DataDog. Requires DataDog App and API keys,
    first and last name of the user in question, and optionally a custom email address."""

    def __init__(self, email=None, *, api_key, app_key, first_name: str, last_name: str) -> None:
        self.header_data = {"DD-API-KEY": api_key, "DD-APPLICATION-KEY": app_key}
        self.first_name = first_name.lower()
        self.last_name = last_name.lower()
        self.full_name = f"{first_name.title()} {last_name.title()}"
        self.service_name = "DataDog"
        if not email:
            self.email = self.first_name + "." + self.last_name + "@*****************.com"
        else:
            self.email = email

    def __create_datadog_user(self) -> dict:
        """Creates user in DataDog."""
        payload = {
            "data": {"attributes": {"email": self.email, "name": self.full_name}, "type": "users"}
        }
        url = "https://api.datadoghq.com/api/v2/users"
        print(f"Sending create user payload to DataDog ({url}):\n{payload}")
        try:
            response = requests.post(url, headers=self.header_data, json=payload)
        except BaseException as err:
            print(f"Error creating DataDog User:\n{err}")
            return {"ok": False, "payload": err}
        print(
            f"Received {response.status_code} response code from DataDog and the following response:\n{response.text}"
        )
        if "errors" in response.json():
            print(f"Error creating DataDog User:\n{response.text}")
            return {"ok": False, "payload": response.json()}
        else:
            print(f"Successfully created DataDog User:\n{response.text}")
            return {"ok": True, "payload": response.json()}

    def __enable_datadog_user(self, uid) -> dict:
        """Re-enable users who have previously been deleted/disabled"""
        payload = {"data": {"attributes": {"disabled": False}, "id": uid, "type": "users"}}
        url = f"https://api.datadoghq.com/api/v2/users/{uid}"

        print(f"Sending re-enable user payload to DataDog ({url}):\n{payload}")
        try:
            response = requests.patch(url, headers=self.header_data, json=payload)
        except BaseException as err:
            print(f"Error re-enabling DataDog User:\n{err}")
            return {"ok": False, "payload": err}

        print(
            f"Received {response.status_code} response code from DataDog and the following response:\n{response.text}"
        )
        if response.status_code != 200:
            print(f"Error re-enabling DataDog User:\n{response.text}")
            return {"ok": False, "payload": response.text}
        else:
            print(f"Successfully re-enabled DataDog User:\n{response.text}")
            return {"ok": True, "payload": response.text}

    def __get_datadog_user_id(self) -> dict:
        """Returns user ID for a given email"""
        payload = {"filter": self.email}
        url = "https://api.datadoghq.com/api/v2/users"

        print(f"Sending find user ID params to DataDog ({url}):\n{payload}")
        try:
            response = requests.get(url, headers=self.header_data, params=payload)
        except BaseException as err:
            print(f"Error obtaining DataDog User ID:\n{err}")
            return {"ok": False, "payload": err}

        print(
            f"Received {response.status_code} response code from DataDog and the following response:\n{response.text}"
        )
        if response.json()["meta"]["page"]["total_filtered_count"] == 0:
            print(f"User not found:\n{response.text}")
            return {"ok": False, "payload": "Email Not Found"}
        else:
            json_response = response.json()
            for user in json_response["data"]:
                if (
                    user["attributes"]["service_account"] is True
                ):  # It's possible for service accounts to share emails with users.
                    continue
                else:
                    user_id = user["id"]
                    print(f"Found the following DataDog UID: {user_id}")
                    return {"ok": True, "payload": user_id}

    def __send_datadog_invite(self, uid: str) -> dict:
        """Triggers the sending of the invite email"""
        payload = {
            "data": [
                {
                    "relationships": {"user": {"data": {"id": uid, "type": "users"}}},
                    "type": "user_invitations",
                }
            ]
        }
        url = "https://api.datadoghq.com/api/v2/user_invitations"

        print(f"Sending invite user payload to DataDog ({url}):\n{payload}")
        try:
            response = requests.post(url, headers=self.header_data, json=payload)
        except BaseException as err:
            print(f"Error Sending DataDog Invite Email:\n{err}")
            return {"ok": False, "payload": err}
        if response.status_code != 201:
            print(f"Error Sending DataDog Invite Email:\n{response.text}")
            return {"ok": False, "payload": response.text}
        else:
            print(f"Successfully Sent DataDog Invite Email:\n{response.text}")
            return {"ok": True, "payload": response.text}

    def __remove_datadog_user(self, uid):
        """Disables a user in DataDog. User isn't actually deleted."""
        url = f"https://api.datadoghq.com/api/v2/users/{uid}"

        print(f"Sending disable user to DataDog: ({url})")
        try:
            response = requests.delete(url, headers=self.header_data)
        except BaseException as err:
            print(f"Error Disabling DataDog User:\n{err}")
            return {"ok": False, "payload": err}
        if response.status_code == 204:
            print("Successfully Disabled DataDog User")
            return {"ok": True, "payload": response.status_code}
        elif response.status_code == 404:
            print(f"Error Disabling DataDog User:\n{response.text}")
            return {"ok": False, "payload": "Email Not Found"}
        else:
            print(f"Error Disabling DataDog User:\n{response.text}")
            return {"ok": False, "payload": response.text}

    def onboard(self) -> None:
        """Handles onboarding process and error handling for DataDog.
        Should be called directly with no arguments."""
        create_datadog_user_response = self.__create_datadog_user()
        if create_datadog_user_response["ok"] is False:
            if "already exists" in create_datadog_user_response["payload"]["errors"][0]:
                # This likely means user was previously disabled and instead we must re-enable
                datadog_user_id_response = self.__get_datadog_user_id()
                if datadog_user_id_response["ok"] is False:
                    return {
                        "ok": False,
                        "message": f"DataDog reports that this user already exists, however I am unable to locate the user ID in DataDog to re-activate the user. We received the following error:\n```{datadog_user_id_response['payload']}```",
                    }
                else:
                    datadog_user_id = datadog_user_id_response["payload"]
                    enable_datadog_user_result = self.__enable_datadog_user(datadog_user_id)
                    if enable_datadog_user_result["ok"] is False:
                        return {
                            "ok": False,
                            "message": f"DataDog reports that this user already exists, but I have encountered an error in DataDog trying to re-activate the user. We received the following error:\n```{enable_datadog_user_result['payload']}```",
                        }
                    else:
                        send_datadog_invite_response = self.__send_datadog_invite(datadog_user_id)
                        if send_datadog_invite_response["ok"] is False:
                            return {
                                "ok": False,
                                "message": f"DataDog reported that the provided user already exists. I have successfully re-activated the disabled user, however there has been an error attempting to trigger the email invite. We received the following error:\n```{send_datadog_invite_response['payload']}```\n\nIt's possible the user is already able to login via OneLogin but if they require an invite you can manually do so from the DataDog UI.",
                            }
                        else:
                            return {
                                "ok": True,
                                "message": "DataDog reported that the provided user already exists. I have successfully re-activated the disabled user, and a new invitation email has been sent. The user must validate their email before access will function.",
                            }
            else:
                return {
                    "ok": False,
                    "message": f"There was an error creating the user in DataDog. We received the following error:\n```{create_datadog_user_response['payload']}```",
                }
        else:  # We get here only if successfully creating the DD user
            datadog_user_id_response = self.__get_datadog_user_id()
            if datadog_user_id_response["ok"] is False:
                return {
                    "ok": False,
                    "message": f"DataDog reported successfully creating the user, however I am unable to locate the user ID in DataDog in order to trigger the email invite. We received the following error:\n```{datadog_user_id_response['payload']}```\n\nYou can manually send the invite from the DataDog UI.",
                }
            else:
                datadog_user_id = datadog_user_id_response["payload"]
                send_datadog_invite_response = self.__send_datadog_invite(datadog_user_id)
                if send_datadog_invite_response["ok"] is False:
                    return {
                        "ok": False,
                        "message": f"DataDog reported successfully creating the user, however there has been an error attempting to trigger the email invite. We received the following error:\n```{send_datadog_invite_response['payload']}```\n\nIt may be possible to manually send the invite from the DataDog UI.",
                    }
                else:
                    return {
                        "ok": True,
                        "message": "Successfully created the user in DataDog, and an invitation email has been sent. The user must validate their email before access will function.",
                    }

    def offboard(self) -> None:
        """Handles offboarding process and error handling for DataDog. Should be called directly."""
        datadog_user_id_response = self.__get_datadog_user_id()
        if datadog_user_id_response["ok"] is False:
            return {
                "ok": False,
                "message": f"I am unable to locate the user ID in DataDog to disable the user. We received the following error:\n```{datadog_user_id_response['payload']}```",
            }
        datadog_user_id = datadog_user_id_response["payload"]

        remove_datadog_user_response = self.__remove_datadog_user(datadog_user_id)
        if remove_datadog_user_response["ok"] is False:
            return {
                "ok": False,
                "message": f"I have encountered an error attempting to disable the user in DataDog. We received the following error:\n```{remove_datadog_user_response['payload']}```",
            }
        else:
            return {"ok": True, "message": "I have successfully disabled the user in DataDog."}
