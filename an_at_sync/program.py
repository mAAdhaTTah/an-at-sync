from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Iterable, List, Optional, Type
from typing_extensions import Literal

from pyairtable import Table as Airtable
from pydantic import BaseModel as PydanticModel
from pydantic import BaseSettings
from rich.console import Console

from an_at_sync.actionnetwork import ActionNetworkApi
from an_at_sync.model import (
    ActivistRepository,
    BaseActivist,
    BaseEvent,
    BaseModel,
    BaseRSVP,
    EventRepository,
    RSVPRepository,
)


class SyncResult(PydanticModel):
    status: Literal["unchanged", "inserted", "updated", "skipped", "failed"]
    kind: Literal["activist", "event", "rsvp", "webhook"]
    instance: Optional[BaseModel]
    e: Optional[Exception]

    class Config:
        arbitrary_types_allowed = True

    def __str__(self):
        return f"Status for {self.instance}: {self.status}" + (
            f" Exception: {self.e}" if self.e else ""
        )


class ProgramSettings(BaseSettings):
    an_api_key: str
    at_base: str
    at_activists_table: str
    at_events_table: str
    at_rsvp_table: str
    at_api_key: str

    class Config:
        env_file = ".env"


class Program:
    @staticmethod
    def load_config(config_path: Path):
        spec = spec_from_file_location("config", config_path)
        if spec is None or spec.loader is None:
            raise Exception("spec or spec.loader for config was None")
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        return module

    def __init__(
        self,
        settings: ProgramSettings,
        activist_class: Type[BaseActivist],
        event_class: Type[BaseEvent],
        rsvp_class: Type[BaseRSVP],
    ):
        an = ActionNetworkApi(api_key=settings.an_api_key)

        self.events = EventRepository(
            an=an,
            at=Airtable(
                settings.at_api_key, settings.at_base, settings.at_events_table
            ),
            klass=event_class,
        )
        self.activists = ActivistRepository(
            an=an,
            at=Airtable(
                settings.at_api_key, settings.at_base, settings.at_activists_table
            ),
            klass=activist_class,
        )
        self.rsvps = RSVPRepository(
            an=an,
            at=Airtable(settings.at_api_key, settings.at_base, settings.at_rsvp_table),
            klass=rsvp_class,
        )
        self.console = Console()

    def sync_activists(self) -> Iterable[SyncResult]:
        for activist in self.activists.all_from_actionnetwork():
            yield self.sync_activist(activist)

    def sync_activist(self, activist: BaseActivist) -> SyncResult:
        try:
            record = self.activists.get_airtable_record(activist)
            insert = record is None
            if insert:
                self.activists.insert_airtable_record(activist)
            else:
                if not self.activists.should_update_airtable_record(activist):
                    return SyncResult(
                        status="unchanged",
                        kind="activist",
                        instance=activist,
                        e=None,
                    )
                self.activists.update_airtable_record(activist)
            return SyncResult(
                status="inserted" if insert else "updated",
                kind="activist",
                instance=activist,
                e=None,
            )
        except Exception as e:
            return SyncResult(status="failed", kind="activist", instance=activist, e=e)

    def sync_events(self) -> Iterable[SyncResult]:
        for event in self.events.all_from_actionnetwork():
            yield self.sync_event(event)

    def sync_event(self, event: BaseEvent) -> SyncResult:
        try:
            record = self.events.get_airtable_record(event)
            insert = record is None
            if insert:
                self.events.insert_airtable_record(event)
            else:
                if not self.events.should_update_airtable_record(event):
                    return SyncResult(
                        status="unchanged",
                        kind="event",
                        instance=event,
                        e=None,
                    )
                self.events.update_airtable_record(event)
            return SyncResult(
                status="inserted" if insert else "updated",
                kind="event",
                instance=event,
                e=None,
            )
        except Exception as e:
            return SyncResult(status="failed", kind="event", instance=event, e=e)

    def sync_rsvps_from_event(self, event: BaseEvent):
        yield from self.sync_rsvps(
            self.rsvps.from_actionnetwork_for_event(
                event,
                events=self.events,
                activists=self.activists,
            ),
        )

    def sync_rsvps(self, rsvps: Iterable[BaseRSVP]):
        for rsvp in rsvps:
            yield self.sync_rsvp(rsvp)

    def sync_rsvp(self, rsvp: BaseRSVP):
        try:
            rsvp_record = self.rsvps.get_airtable_record(rsvp)
            insert = rsvp_record is None
            if insert:
                self.rsvps.insert_airtable_record(
                    rsvp,
                    activist_record=self.activists.get_airtable_record(rsvp.activist),
                    event_record=self.events.get_airtable_record(rsvp.event),
                )
            else:
                if not self.rsvps.should_update_airtable_record(rsvp):
                    return SyncResult(
                        status="unchanged",
                        kind="rsvp",
                        instance=rsvp,
                        e=None,
                    )
                self.rsvps.update_airtable_record(rsvp)
            return SyncResult(
                status="inserted" if insert else "updated",
                kind="rsvp",
                instance=rsvp,
                e=None,
            )
        except Exception as e:
            return SyncResult(status="failed", kind="event", instance=rsvp, e=e)

    def handle_webhook(self, webhook_body: List[dict]):
        for webhook_event in webhook_body:
            attendance = webhook_event.get("osdi:attendance")
            if attendance is None:
                yield SyncResult(status="skipped", kind="webhook")
                continue
            activist = self.activists.from_actionnetwork_url(
                attendance["_links"]["osdi:person"]["href"],
                custom_fields=attendance["_links"]["osdi:person"].get("custom_fields"),
            )
            yield self.sync_activist(activist)

            event = self.events.from_actionnetwork_url(
                attendance["_links"]["osdi:event"]["href"],
                custom_fields=attendance["_links"]["osdi:person"].get("custom_fields"),
            )
            yield self.sync_event(event)

            rsvp = self.rsvps.klass.from_actionnetwork(
                attendance,
                activist=activist,
                event=event,
                activist_record=self.activists.get_airtable_record(activist),
                event_record=self.events.get_airtable_record(event),
            )
            yield self.sync_rsvp(rsvp)

    def write_result(self, result: SyncResult):
        display_name = (" " + result.instance.display_name()) if result.instance else ""
        # TODO(mAAdhaTTah) convert to match when 3.10 is min version
        if result.status == "unchanged":
            self.console.print(":information:", end=" ")
            self.console.print(
                f"Syncing {result.kind}{display_name} resulted in no changes"
            )
        elif result.status == "inserted":
            self.console.print(":heavy_plus_sign:", end=" ")
            self.console.print(
                f"Syncing {result.kind}{display_name} inserted new model"
            )
        elif result.status == "updated":
            self.console.print(":white_check_mark:", end=" ")
            self.console.print(f"Syncing {result.kind}{display_name} succeeded")
        elif result.status == "failed":
            self.console.print(":x:", end=" ")
            self.console.print(
                f"Syncing {result.kind}{display_name} failed with error:"
            )
            self.console.print(result.e)
        elif result.status == "skipped":
            self.console.print(":information:", end=" ")
            self.console.print(f"{result.kind}{display_name} was skipped")
        else:
            raise Exception(f"Unhandled status {result.status}")
