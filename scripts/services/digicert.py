"""Module to handle on and offboarding of users in DigiCert."""
import requests


class DigiCertOnBoarder:
    """Class to handle on and offboarding of users in DigiCert. Requires DigiCert credentials,
    first and last name of the user in question, and optionally a custom email address."""

    def __init__(self, email=None, *, api_key, first_name, last_name) -> None:
        self.first_name = first_name.lower()
        self.last_name = last_name.lower()
        self.full_name = first_name.title() + " " + last_name.title()
        if not email:
            self.email = self.first_name + "." + self.last_name + "@*****************.com"
        else:
            self.email = email
        self.headers = {"X-DC-DEVKEY": api_key}
        self.service_name = "DigiCert"

    def __get_user_id(self) -> str:
        url = "https://www.digicert.com/services/v2/user"
        params = {"filters[search]": self.email}

        response = requests.get(url, headers=self.headers, params=params)

        if "users" not in response.json():
            print(f"Error looking for User ID:\n{response.text}")
            return None

        try:
            result_set = response.json()["users"]
        except:
            print(f"Error looking for User ID:\n{response.text}")
            return None

        for user in result_set:
            if user["email"].casefold() == self.email.casefold():
                return user["id"]
        return None

    def onboard(self):
        """Handles the process of onboarding the user"""
        url = "https://www.digicert.com/services/v2/user"

        payload = {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "username": self.email,
            "container": {"id": 91802},  # SaaSOps
            "access_roles": [{"id": 5}],  # Standard User
            "is_saml_sso_only": True,
        }

        try:
            response = requests.post(url, json=payload, headers=self.headers)
        except BaseException as err:
            print(f"Error connecting to DigiCert:\n{err}")
            return {
                "ok": False,
                "message": f"I've encountered an error connecting to the DigiCert API. Here's what I received:\n```{err}```",
            }

        if response.status_code == 201:
            return {"ok": True, "message": "I have successfully created the user in DigiCert."}
        else:
            return {
                "ok": False,
                "message": f"Received {response.status_code} status code from DigiCert when attempting to create the user. Here's what I received:\n```{response.text}```",
            }

    def offboard(self):
        """Handles the process of offboarding the user"""
        try:
            user_id = self.__get_user_id()
        except BaseException as err:
            print(f"Error Deleting DigiCert user:\n{err}")
            return {
                "ok": False,
                "message": f"I've encountered an error finding the userID in DigiCert. No users have been removed. Here's what I received:\n```{err}```",
            }

        if user_id is None:
            return {
                "ok": False,
                "message": "I've encountered an error finding the userID in DigiCert. No users have been removed. Here's what I received:\n```Email Not found```",
            }

        try:
            url = f"https://www.digicert.com/services/v2/user/{user_id}"
            response = requests.delete(url, headers=self.headers)
        except BaseException as err:
            print(f"Error Deleting DigiCert user:\n{err}")
            return {
                "ok": False,
                "message": f"I've encountered an error connecting to the DigiCert API. Here's what I received:\n```{err}```",
            }

        if response.status_code == 204:
            return {"ok": True, "message": "I have successfully deleted the user in DigiCert."}
        else:
            return {
                "ok": False,
                "message": f"Received {response.status_code} status code from DigiCert when attempting to delete the user. Here's what I received:\n```{response.text}```",
            }
