# an-at-sync

Python package & cli for syncing between ActionNetwork & AirTable.

## How to Use

To set up a new project with `an-at-sync`, create a new folder for your project:

```sh
mkdir project-name && cd project-name
```

In that folder, create a `requirements.txt` and add `an-at-sync` as a dependency:

```
an-at-sync
```

Install it with pip:

```sh
pip install -r requirements.txt
```

Create a folder for your project namespace:

```
mkdir project_name
```

In that folder, create a `models.py` with this default content:

```py
from datetime import datetime
from typing import Any, Dict, Optional

from an_at_sync.format import convert_adr, standardize_phone
from an_at_sync.model import BaseActivist, BaseEvent, BaseRSVP
from dateutil import tz
from pyairtable.utils import datetime_to_iso_str
from pydantic import HttpUrl, validator
from pydantic.networks import EmailStr

eastern = tz.gettz("America/New_York")
utc = tz.gettz("UTC")


class Activist(BaseActivist):
    first_name: Optional[str]
    last_name: Optional[str]
    email: EmailStr
    zip_code: Optional[str]
    phone_number: Optional[str]
    address: Optional[str]
    city: Optional[str]
    state: Optional[str]

    @classmethod
    def from_actionnetwork(cls, source: dict, **kwargs: Any):
        address, city, state, zip_code = convert_adr(source["postal_addresses"][0])
        return cls(
            first_name=source.get("given_name"),
            last_name=source.get("family_name"),
            email=source["email_addresses"][0]["address"].strip(),
            address=address,
            city=city,
            state=state,
            zip_code=zip_code,
            phone_number=standardize_phone(source["phone_numbers"][0].get("number")),
        )

    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def pk(self) -> Dict:
        return {"Email": self.email}

    def to_airtable(self):
        return {
            "Email": self.email,
            "First Name": self.first_name,
            "Last Name": self.last_name,
            "Phone": self.phone_number,
            "Address": self.address,
            "City": self.city,
            "State": self.state,
            "Zip": self.zip_code,
        }


class RSVP(BaseRSVP):
    id: str
    rsvpd_at: datetime

    @classmethod
    def from_actionnetwork(cls, source, **kwargs: Any):
        return cls(
            id=f"{kwargs['activist_record']['id']}-{kwargs['event_record']['id']}",
            activist=kwargs["activist"],
            event=kwargs["event"],
            rsvpd_at=source["created_date"],
        )

    def display_name(self) -> str:
        return f"{self.activist.display_name()} to {self.event.display_name()}"

    def pk(self):
        return {"Id": self.id}

    def to_airtable(self) -> dict:
        return {
            "Id": self.id,
            "RSVP'd At": datetime_to_iso_str(self.rsvpd_at.replace(tzinfo=None)),
        }

    def activist_column(self) -> str:
        return "Volunteer"

    def event_column(self) -> str:
        return "Event"


class Event(BaseEvent):
    url: HttpUrl
    name: str
    location: str
    start_date: datetime
    end_date: Optional[datetime]
    status: str

    @validator("start_date", "end_date")
    def dates_must_be_eastern(cls, v: datetime):
        return v.replace(tzinfo=eastern) if v is not None else v

    @classmethod
    def from_actionnetwork(cls, source: dict, **kwargs):
        address, city, state, *_ = convert_adr(source["location"])
        event_location = "Zoom" if not address else f"{address}, {city}, {state}"
        return cls(
            url=source["browser_url"],
            name=source["title"],
            start_date=source["start_date"],
            end_date=source.get("end_date"),
            status=source["status"],
            location=event_location,
        )

    def display_name(self) -> str:
        return self.name

    def pk(self) -> Dict:
        return {"Url": str(self.url)}

    def to_airtable(self) -> dict:
        return {
            "Url": str(self.url),
            "Name": self.name,
            "Start At": self.start_date.astimezone(tz=utc)
            .replace(tzinfo=None)
            .isoformat(timespec="milliseconds")
            + "Z",
            "End At": self.end_date.astimezone(tz=utc)
            .replace(tzinfo=None)
            .isoformat(timespec="milliseconds")
            + "Z"
            if self.end_date
            else None,
            "Status": self.status.capitalize(),
            "Location": self.location,
        }

```

These models represent the various part of the system we're going to interact independently from the two systems that will use them. The Activist represents an individual person in your campaign. The Event represents a single campaign event, and an RSVP represents a response from an Activist to attend an event.

You can use this as a baseline for your own models, allowing you to customize which fields are synced to AirTable & how.

Next, create this `.env` file:

```sh
AN_AT_SYNC_MODELS="project_name.models"
AN_API_KEY="TODO: ActionNetwork API Key"
AT_API_KEY="TODO: Airtable API Key"
AT_BASE="TODO: Base"
AT_ACTIVISTS_TABLE="TODO: Volunteers Table"
AT_EVENTS_TABLE="TODO: Events Table"
AT_RSVP_TABLE="TODO: RSVP Table"
```

Given the `project_name` above, the `AN_AT_SYNC_MODELS` points to the module that `an-at-sync` can load our custom models from. The rest of the env vars require you to get the proper keys and configure your AirTable account.

### Getting Your ActionNetwork API Key

Details -> API & Sync. "Your API Key" -> Generate Key. Copy into `.env`.

### Creating Your AirTable Base

Need to create the base first. Create Volunteers, Events, & RSVPs table. Get base id from first part of the URL (starts with `app`).

### Getting Your AirTable API Key

User stetings -> Developer Hub -> Personal Access token. `data.records:read` & `data.records:write`. Access to the created base. Copy the token, add to `.env.`

### Creating Your AirTable Volunteers Table

Create fields returned by `to_airtable` method. Copy from second part of URL and add to `.env`.

### Creating Your AirTAble Events Table

Create fields returned by `to_airtable` method. Copy from second part of URL and add to `.env`.

### Creating Your AirTable RSVP Table

Create fields returned by `to_airtable` method. Copy from second part of URL and add to `.env`.

### Run your first sync!

```sh
python -m an_at_sync sync events --rsvps
```
