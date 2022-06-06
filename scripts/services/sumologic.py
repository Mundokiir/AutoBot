"""Module to handle on and offboarding of users in SumoLogic."""
import json
import sys
import http.cookiejar as cookielib
import requests


class SumoLogicOnBoarder(object):
    """Class to handle on and offboarding of users in SumoLogic. Requires SumoLogic access id and key,
    first and last name of the user in question, and optionally a custom email address."""

    def __init__(
        self,
        endpoint=None,
        caBundle=None,
        cookieFile="cookies.txt",
        email=None,
        *,
        access_id,
        access_key,
        first_name,
        last_name,
    ):
        self.session = requests.Session()
        self.session.auth = (access_id, access_key)
        self.DEFAULT_VERSION = "v1"
        self.session.headers = {"content-type": "application/json", "accept": "application/json"}
        if caBundle is not None:
            self.session.verify = caBundle
        cookie_jar = cookielib.FileCookieJar(cookieFile)
        self.session.cookies = cookie_jar
        if endpoint is None:
            self.endpoint = self._get_endpoint()
        else:
            self.endpoint = endpoint
        if self.endpoint[-1:] == "/":
            raise Exception("Endpoint should not end with a slash character")
        self.first_name = first_name.lower()
        self.last_name = last_name.lower()
        self.full_name = f"{first_name.title()} {last_name.title()}"
        self.service_name = "SumoLogic"
        if email is None:
            self.email = self.first_name + "." + self.last_name + "@*****************.com"
        else:
            self.email = email

    def _get_endpoint(self):
        """
        SumoLogic REST API endpoint changes based on the geo location of the client.
        For example, If the client geolocation is Australia then the REST end point is
        https://api.au.sumologic.com/api/v1
        When the default REST endpoint (https://api.sumologic.com/api/v1) is used the server
        responds with a 401 and causes the SumoLogic class instantiation to fail and this very
        unhelpful message is shown 'Full authentication is required to access this resource'
        This method makes a request to the default REST endpoint and resolves the 401 to learn
        the right endpoint
        """

        self.endpoint = "https://api.sumologic.com/api"
        self.response = self.session.get(
            "https://api.sumologic.com/api/v1/collectors"
        )  # Dummy call to get endpoint
        endpoint = self.response.url.replace(
            "/v1/collectors", ""
        )  # dirty hack to sanitize URI and retain domain
        print("SDK Endpoint", endpoint, file=sys.stderr)
        return endpoint

    def get_versioned_endpoint(self, version):
        return f"{self.endpoint}/{version}"

    def delete(self, method, params=None, version=None):
        version = version or self.DEFAULT_VERSION
        endpoint = self.get_versioned_endpoint(version)
        r = self.session.delete(endpoint + method, params=params)
        if 400 <= r.status_code < 600:
            r.reason = r.text
        r.raise_for_status()
        return r

    def get(self, method, params=None, version=None):
        version = version or self.DEFAULT_VERSION
        endpoint = self.get_versioned_endpoint(version)
        r = self.session.get(endpoint + method, params=params)
        if 400 <= r.status_code < 600:
            r.reason = r.text
        r.raise_for_status()
        return r

    def post(self, method, params, headers=None, version=None):
        version = version or self.DEFAULT_VERSION
        endpoint = self.get_versioned_endpoint(version)
        r = self.session.post(endpoint + method, data=json.dumps(params), headers=headers)
        if 400 <= r.status_code < 600:
            r.reason = r.text
        r.raise_for_status()
        return r

    def put(self, method, params, headers=None, version=None):
        version = version or self.DEFAULT_VERSION
        endpoint = self.get_versioned_endpoint(version)
        r = self.session.put(endpoint + method, data=json.dumps(params), headers=headers)
        if 400 <= r.status_code < 600:
            r.reason = r.text
        r.raise_for_status()
        return r

    def get_roles(self):
        return json.dumps(self.get("/roles/").json(), indent=4)

    def find_userid(self):
        params = {"email": self.email}
        result = self.get("/users/", params=params)
        try:
            uid = result.json()["data"][0]["id"]
        except:
            return None
        else:
            return uid

    def onboard(self):
        params = {
            "firstName": self.first_name,
            "lastName": self.last_name,
            "email": self.email,
            "roleIds": ["*****************"],
        }
        try:
            result = self.post("/users/", params=params)
        except BaseException as err:
            return {
                "ok": False,
                "message": f"I've encountered an error connecting to the SumoLogic API. Here's what I received:\n```{err}```",
            }
        if result.status_code == 200:
            return {"ok": True, "message": "I have successfully created the user in SumoLogic."}
        else:
            return {
                "ok": False,
                "message": f"Received {result.status_code} status code from Sumo when attempting to create the user. Here's what I received:\n```{result.text}```",
            }

    def offboard(self):
        try:
            uid = self.find_userid()
        except BaseException as err:
            return {
                "ok": False,
                "message": f"I've encountered an error finding the userID in SumoLogic. No users have been removed. Here's what I received:\n```{err}```",
            }
        if uid is None:
            return {
                "ok": False,
                "message": "I've encountered an error finding the userID in SumoLogic. No users have been removed. Here's what I received:\n```Email Not found```",
            }
        try:
            result = self.delete(f"/users/{uid}")
        except BaseException as err:
            return {
                "ok": False,
                "message": f"I've encountered an error connecting to the SumoLogic API. Here's what I received:\n```{err}```",
            }
        if result.status_code == 204:
            return {"ok": True, "message": "I have successfully deleted the user in SumoLogic."}
        else:
            return {
                "ok": False,
                "message": f"Received {result.status_code} status code from Sumo when attempting to delete the user. Here's what I received:\n```{result.text}```",
            }
