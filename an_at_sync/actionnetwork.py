from typing import Iterable

import requests
from pyactionnetwork import ActionNetworkApi as BaseApi


class ActionNetworkApi(BaseApi):
    def get_all_activists(self) -> Iterable[dict]:
        url = self.resource_to_url("people")
        while url:
            body = requests.get(url, headers=self.headers).json()
            for activist in body.get("_embedded", {}).get("osdi:people", []):
                yield activist

            next_link = body["_links"].get("next")
            url = next_link.get("href") if next_link else None

    def get_all_events(self):
        url = self.resource_to_url("events")
        while url:
            body = requests.get(url, headers=self.headers).json()
            for event in body.get("_embedded").get("osdi:events"):
                yield event

            next_link = body["_links"].get("next")
            url = next_link.get("href") if next_link else None

    def get_event(self, event):
        url = self.resource_to_url("events")
        return requests.get(f"{url}/{event}", headers=self.headers).json()

    def get_attendances_from_event(self, event: dict):
        next_href = event["_links"]["osdi:attendances"]["href"]

        while next_href:
            response = requests.get(next_href, headers=self.headers)
            attendances_body = response.json()

            for attendance in attendances_body["_embedded"]["osdi:attendances"]:
                person_url = attendance["_links"]["osdi:person"]["href"]
                person_body = requests.get(person_url, headers=self.headers).json()
                yield person_body

            try:
                next_href = attendances_body["_links"]["next"]["href"]
            except KeyError:
                next_href = None
