"""Module to handle on and offboarding of users in AlertSite."""
import random
import string
import requests


class AlertSiteOnBoarder:
    """Class to handle on and offboarding of users in AlertSite. Requires AlertSite credentials,
    first and last name of the user in question, and optionally a custom email address."""

    def __init__(self, email=None, *, user, passwd, first_name, last_name) -> None:
        self.first_name = first_name.lower()
        self.last_name = last_name.lower()
        self.full_name = first_name.title() + " " + last_name.title()
        if not email:
            self.email = self.first_name + "." + self.last_name + "@*****************.com"
        else:
            self.email = email

        # All AlertSite API calls require an auth token first
        payload = {"username": user, "password": passwd}
        url = "https://api.alertsite.com/api/v3/access-tokens"
        print(f"Sending authentication payload to AlertSite ({url})")
        try:
            response = requests.post(url, json=payload)
        except BaseException as err:
            print(f"Error obtaining AlertSite authentication token:\n{err}")
            self.token = {"ok": False, "payload": err}
        else:
            try:
                json_response = response.json()
                token = json_response["access_token"]
            except BaseException:
                print(f"Error obtaining AlertSite authentication token:\n{response.text}")
                self.token = {"ok": False, "payload": response.text}
            else:
                self.token = {"ok": True, "token": token}
                print(f"Successfully obtained AlertSite authentication token: {token}")

    def __create_alertsite_user(self) -> dict:
        """Create user in AlertSite"""
        header_data = {"Authorization": f"Bearer {self.token['token']}"}
        payload = {
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "password": "".join(random.choice(string.ascii_letters) for i in range(12)),
            "work_phone": "5551234",  # Fake phone number, field is required.
            "role": "READONLY",  # Policy decision. Can manually change if needed.
        }
        try:
            response = requests.post(
                "https://api.alertsite.com/api/v3/users", headers=header_data, json=payload
            )
        except BaseException as err:
            print(f"Error creating AlertSite user:\n{err}")
            return {"ok": False, "payload": err}

        if "id" not in response.json():
            print(f"Error creating AlertSite user:\n{response.text}")
            result = {"ok": False, "payload": response.text}
        else:
            result = {"ok": True, "payload": response.text}
            print(f"Successfully created AlertSite user: {response.text}")
        return result

    def __find_alertsite_user_id(self) -> dict:
        """Returns user ID for a user in AlertSite. We have to pull every single user
        and iterate through them for the one that matches our email"""
        header_data = {"Authorization": f"Bearer {self.token['token']}"}
        print("Requesting user data from AlertSite for ID purposes...")
        try:
            response = requests.get(
                "https://api.alertsite.com/api/v3/users", headers=header_data, json={}
            )
            print(f"Received response code {response.status_code} from AlertSite")
        except BaseException as err:
            print(f"Error obtaining AlertSite user ID:\n{err}")
            result = {"ok": False, "payload": err}
            return result
        try:
            result_set = response.json()["results"]
        except BaseException as err:
            print(f"Error obtaining AlertSite user ID:\n{response.text}")
            return {"ok": False, "payload": err}
        for user in result_set:
            if user["email"].casefold() == self.email.casefold():
                return {"ok": True, "payload": user["guid"]}
        return {"ok": False, "payload": "Email Not found"}

    def __remove_alertsite_user(self, guid) -> dict:
        """ "Deletes user from AlertSite"""
        header_data = {"Authorization": f"Bearer {self.token['token']}"}
        print(f"Attempting to delete {guid} from AlertSite")
        try:
            response = requests.delete(
                f"https://api.alertsite.com/api/v3/users/{guid}", headers=header_data, json={}
            )
            print(f"Received status code {response.status_code} during delete attempt")
        except BaseException as err:
            print(f"Error deleting AlertSite user:\n{err}")
            result = {"ok": False, "payload": err}
            return result
        if response.status_code != 204:
            print(f"Error deleting AlertSite user:\n{response.text}")
            result = {"ok": False, "payload": response.text}
        else:
            print("Successfully deleted AlertSite User")
            result = {"ok": True, "payload": response.status_code}
            return result

    def onboard(self) -> None:
        """Handles all steps required for onboarding AlertSite users"""
        if self.token["ok"] is False:
            return {
                "ok": False,
                "message": f"There was an error obtaining an authentication token from AlertSite. No users have been created. We received the following error:\n```{self.token['payload']}```",
            }

        create_alertsite_user_response = self.__create_alertsite_user()
        if create_alertsite_user_response["ok"] is False:
            return {
                "ok": False,
                "message": f"There was an error trying to create the user in AlertSite. We received the following error:\n```{create_alertsite_user_response['payload']}```",
            }
        return {"ok": True, "message": "I have successfully created the user in AlertSite."}

    def offboard(self) -> None:
        """Handles all steps required for offboarding AlertSite users"""
        if self.token["ok"] is False:
            return {
                "ok": False,
                "message": f"There was an error obtaining an authentication token from AlertSite. No users have been created. We received the following error:\n```{self.token['payload']}```",
            }

        user_id_response = self.__find_alertsite_user_id()
        if user_id_response["ok"] is False:
            return {
                "ok": False,
                "message": f"There was an error finding the user ID from AlertSite. No users have been removed. We received the following error:\n```{user_id_response['payload']}```",
            }
        alertsite_user_id = user_id_response["payload"]

        remove_alertsite_user_result = self.__remove_alertsite_user(alertsite_user_id)
        if remove_alertsite_user_result["ok"] is False:
            return {
                "ok": False,
                "message": f"There was an error deleting the user from AlertSite. No users have been removed. We received the following error:\n```{remove_alertsite_user_result['payload']}```",
            }
        return {"ok": True, "message": "I have successfully deleted the user from AlertSite"}
