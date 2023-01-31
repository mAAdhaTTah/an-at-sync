from typing import Iterable
from urllib.parse import quote

from requests import Session


class ActionNetworkApi:
    """
    Python wrapper for Action Network API.

    Cribbed primarily from https://github.com/PhillyDSA/pyactionnetwork
    with some added methods & typing.
    """

    def __init__(self, api_key, **kwargs):
        """Instantiate the API client and get config."""
        self.session = Session()
        self.session.headers.update({"OSDI-API-Token": api_key})
        self.refresh_config()
        self.base_url = self.config.get("links", {}).get(
            "self", "https://actionnetwork.org/api/v2/"
        )

    def refresh_config(self):
        """Get a new version of the base_url config."""
        self.config = self.session.get(url="https://actionnetwork.org/api/v2/").json()

    def resource_to_url(self, resource):
        """Convert a named endpoint into a URL.
        Args:
            resource (str):
                resource name (e.g. 'links', 'people', etc.)
        Returns:
            (str) Full resource endpoint URL.
        """
        if resource in self.config.get("_links", {}).keys():
            return self.config["_links"][resource]["href"]
        try:
            return self.config["_links"]["osdi:{0}".format(resource)]["href"]
        except KeyError:
            raise KeyError("Unknown Resource %s", resource)

    def get_resource(self, resource):
        """Get a resource endpoint by name.
        Args:
            resource (str):
                Resource endpoint of the format 'people', 'events', 'lists', etc.
        Returns:
            (dict) API response from endpoint or `None` if not found/valid.
        """
        url = self.resource_to_url(resource)
        return self.session.get(url).json()

    def get_person(self, person_id=None, search_by="email", search_string=None):
        """Search for a user.
        Args:
            search_by (str):
                Field by which to search for a user. 'email' is the default.
            search_string (str):
                String to search for within the field given by `search_by`
        Returns:
            (dict) person json if found, otherwise `None`
        """
        if person_id:
            url = "{0}people/{1}".format(self.base_url, person_id)
        else:
            url = "{0}people/?filter={1} eq '{2}'".format(
                self.base_url, search_by, quote(search_string)
            )

        resp = self.session.get(url)
        return resp.json()

    def create_person(
        self,
        email=None,
        given_name="",
        family_name="",
        address=list(),
        city="",
        state="",
        country="",
        postal_code="",
        tags=list(),
        custom_fields=dict(),
    ):
        """Create a user.
        Documentation here: https://actionnetwork.org/docs/v2/person_signup_helper
        Args:
            email ((str, list)):
                email address (or, if list, addresses) of the person
            given_name (str, optional):
                first name of the person
            family_name (str, optional):
                last name of the person
            address ((str, list), optional):
                address of the person. if a str, then one address line
                only. if a list, then address_lines in action network
                will be respected (for apartments or companies etc.)
            city (str, optional):
                city of the person.
            country (str, optional):
                country code for the person.
            postal_code (str, optional):
                postal or zip code of the person.
            tags ((str, list), optional):
                add any tags you want when creating a person.
            custom_fields (dict, optional):
                dict of custom fields to pass to the api
        Returns:
            (dict) A fully fleshed out dictionary representing a person,
            containing the above attributes and additional attributes
            set by Action Network.
        """
        url = "{0}people/".format(self.base_url)
        payload = {
            "person": {
                "family_name": family_name,
                "given_name": given_name,
                "postal_addresses": [
                    {
                        "address_lines": list(address),
                        "locality": city,
                        "region": state,
                        "country": country,
                        "postal_code": postal_code,
                    }
                ],
                "email_addresses": [{"address": email}],
                "custom_fields": custom_fields,
            },
            "add_tags": list(tags),
        }

        resp = self.session.post(url, json=payload)
        return resp.json()

    def update_person(
        self,
        person_id=None,
        email=None,
        given_name=None,
        family_name=None,
        address=list(),
        city=None,
        state=None,
        country=None,
        postal_code=None,
        tags=list(),
        custom_fields=dict(),
    ):
        """Update a user.
        Args:
            email ((str, list)):
                email address (or, if list, addresses) of the person
            given_name (str, optional):
                first name of the person
            family_name (str, optional):
                last name of the person
            address ((str, list), optional):
                address of the person. if a str, then one address line
                only. if a list, then address_lines in action network
                will be respected (for apartments or companies etc.)
            city (str, optional):
                city of the person.
            country (str, optional):
                country code for the person.
            postal_code (str, optional):
                postal or zip code of the person.
            tags ((str, list), optional):
                add any tags you want when creating a person.
            custom_fields (dict, optional):
                dict of custom fields to pass to the api
        Returns:
            (dict) A fully fleshed out dictionary representing a person, containing the above
            attributes and additional attributes set by Action Network.
        """
        url = "{0}people/{1}".format(self.base_url, person_id)
        payload = {
            "family_name": family_name,
            "given_name": given_name,
            "postal_addresses": [
                {
                    "address_lines": list(address),
                    "locality": city,
                    "region": state,
                    "country": country,
                    "postal_code": postal_code,
                }
            ],
            "email_addresses": [{"address": email}],
            "add_tags": list(tags),
            "custom_fields": custom_fields,
        }

        return self.session.put(url, json=payload).json()

    def get_all_activists(self) -> Iterable[dict]:
        url = self.resource_to_url("people")
        while url:
            body = self.session.get(url).json()
            for activist in body.get("_embedded", {}).get("osdi:people", []):
                yield activist

            next_link = body["_links"].get("next")
            url = next_link.get("href") if next_link else None

    def get_all_events(self):
        url = self.resource_to_url("events")
        while url:
            body = self.session.get(url).json()
            for event in body.get("_embedded").get("osdi:events"):
                yield event

            next_link = body["_links"].get("next")
            url = next_link.get("href") if next_link else None

    def get_event(self, event):
        url = self.resource_to_url("events")
        return self.session.get(f"{url}/{event}").json()

    def get_attendances_from_event(self, event: dict):
        next_href = event["_links"]["osdi:attendances"]["href"]

        while next_href:
            attendances_body = self.session.get(next_href).json()
            yield from attendances_body["_embedded"]["osdi:attendances"]

            try:
                next_href = attendances_body["_links"]["next"]["href"]
            except KeyError:
                next_href = None
