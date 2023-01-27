from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Generator, List, Optional, Type, Union
from typing_extensions import Literal

from pyairtable import Table as Airtable
from pyairtable.formulas import match
from pydantic import BaseModel as PydanticModel
from pydantic import BaseSettings
from rich.console import Console

from an_at_sync.actionnetwork import ActionNetworkApi
from an_at_sync.model import BaseActivist, BaseEvent, BaseModel, BaseRSVP


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
    an: ActionNetworkApi
    at_events: Airtable
    at_activists: Airtable
    console: Console

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
        self.an = ActionNetworkApi(api_key=settings.an_api_key)
        self.at_activists = Airtable(
            settings.at_api_key, settings.at_base, settings.at_activists_table
        )
        self.at_events = Airtable(
            settings.at_api_key, settings.at_base, settings.at_events_table
        )
        self.at_rsvps = Airtable(
            settings.at_api_key, settings.at_base, settings.at_rsvp_table
        )
        self.activist_class = activist_class
        self.event_class = event_class
        self.rsvp_class = rsvp_class
        self.console = Console()

    def match_activist(self, activist: BaseActivist):
        return self.at_activists.first(formula=match(activist.pk()))

    def sync_activists(self) -> Generator[SyncResult, None, None]:
        for activist in self._get_all_activists():
            activist_result = (
                activist
                if isinstance(activist, SyncResult)
                else self.sync_activist(activist)
            )
            yield activist_result

    def sync_activist(self, activist: BaseActivist) -> SyncResult:
        try:
            record = self.match_activist(activist)
            insert = record is None
            if insert:
                self.at_activists.create(activist.to_airtable())
            else:
                fields = record["fields"]
                update = activist.to_airtable()
                if update == {key: fields.get(key, "") for key in update}:
                    return SyncResult(
                        status="unchanged",
                        kind="activist",
                        instance=activist,
                        e=None,
                    )
                self.at_activists.update(record["id"], update)
            return SyncResult(
                status="inserted" if insert else "updated",
                kind="activist",
                instance=activist,
                e=None,
            )
        except Exception as e:
            return SyncResult(status="failed", kind="activist", instance=activist, e=e)

    def match_event(self, event: BaseEvent):
        return self.at_events.first(formula=match(event.pk()))

    def sync_events(self):
        for event in self._get_all_events():
            event_result = (
                event if isinstance(event, SyncResult) else self.sync_event(event)
            )
            yield event_result
            if event_result.status != "failed":
                yield from self.sync_rsvps_from_event_result(event_result)

    def sync_event(self, event: BaseEvent):
        try:
            record = self.match_event(event)
            insert = record is None
            if insert:
                self.at_events.create(event.to_airtable())
            else:
                fields = record["fields"]
                update = event.to_airtable()
                if update == {
                    key: fields[key] if key in fields else None for key in update
                }:
                    return SyncResult(
                        status="unchanged",
                        kind="event",
                        instance=event,
                        e=None,
                    )
                self.at_events.update(record["id"], update)
            return SyncResult(
                status="inserted" if insert else "updated",
                kind="event",
                instance=event,
                e=None,
            )
        except Exception as e:
            return SyncResult(status="failed", kind="event", instance=event, e=e)

    def sync_rsvps_from_event_result(self, result: SyncResult):
        if (
            result.status != "failed"
            and isinstance(result.instance, BaseEvent)
            and result.instance.rsvps
        ):
            yield from self.sync_rsvps(result.instance.rsvps)

    def sync_rsvps(self, rsvps: List[BaseRSVP]):
        for rsvp in rsvps:
            yield self.sync_rsvp(rsvp)

    def sync_rsvp(self, rsvp: BaseRSVP):
        try:
            activist_record = self.match_activist(rsvp.activist)
            activist_record_id = activist_record["id"] if activist_record else None
            if activist_record_id is None:
                activist_record = self.at_activists.create(rsvp.activist.to_airtable())
                activist_record_id = activist_record["id"]

            event_record = self.match_event(rsvp.event)
            event_record_id = event_record["id"] if event_record else None
            if event_record_id is None:
                event_record = self.at_events.create(rsvp.event.to_airtable())
                event_record_id = event_record["id"]

            """
            WARNING: Extract this logic if we find ourselves needing it elsewhere
            """
            rsvp_id = f"{activist_record_id}-{event_record_id}"
            rsvp_record = self.at_rsvps.first(
                formula=match({rsvp.id_column(): rsvp_id})
            )
            insert = rsvp_record is None
            if insert:
                self.at_rsvps.create(
                    {
                        rsvp.id_column(): rsvp_id,
                        rsvp.activist_column(): [activist_record_id],
                        rsvp.event_column(): [event_record_id],
                    }
                )
                return SyncResult(
                    status="inserted",
                    kind="rsvp",
                    instance=rsvp,
                    e=None,
                )

            return SyncResult(
                status="unchanged",
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

            an_person = self.an.session.get(
                attendance["_links"]["osdi:person"]["href"]
            ).json()
            activist = self.activist_class.from_actionnetwork(
                an_person,
                custom_fields=attendance["_links"]["osdi:person"].get("custom_fields"),
            )
            yield self.sync_activist(activist=activist)

            an_event = self.an.session.get(
                attendance["_links"]["osdi:event"]["href"]
            ).json()
            event = self.event_class.from_actionnetwork(
                an_event,
                custom_fields=attendance["_links"]["osdi:person"].get("custom_fields"),
            )
            yield self.sync_event(event)

            rsvp = self.rsvp_class(activist=activist, event=event)
            yield self.sync_rsvp(rsvp)

    def write_result(self, result: SyncResult):
        # TODO(mAAdhaTTah) convert to match when 3.10 is min version
        if result.status == "unchanged":
            self.console.print(":information:", end=" ")
            self.console.print(f"Syncing {result.kind} resulted in no changes")
        elif result.status == "inserted":
            self.console.print(":heavy_plus_sign:", end=" ")
            self.console.print(f"Syncing {result.kind} inserted new model")
        elif result.status == "updated":
            self.console.print(":white_check_mark:", end=" ")
            self.console.print(f"Syncing {result.kind} succeeded")
        elif result.status == "failed":
            self.console.print(":x:", end=" ")
            self.console.print(f"Syncing {result.kind} failed with error:")
            self.console.print(result.e)
        elif result.status == "skipped":
            self.console.print(":information:", end=" ")
            self.console.print(f"{result.kind} was skipped")
        else:
            raise Exception(f"Unhandled status {result.status}")

    def _get_all_activists(self):
        for activist in self.an.get_all_activists():
            try:
                yield self.activist_class.from_actionnetwork(activist)
            except Exception as e:
                yield SyncResult(status="failed", kind="activist", e=e)

    def _get_all_events(self) -> Generator[Union[BaseEvent, SyncResult], Any, Any]:
        for event in self.an.get_all_events():
            try:
                event_instance: BaseEvent = self.event_class.from_actionnetwork(event)
                yield from event_instance.finalize(self, event)
            except Exception as e:
                yield SyncResult(status="failed", kind="event", e=e)

    def _get_rsvps_from_event(self, event: dict) -> Generator[BaseRSVP, Any, Any]:
        for attendance in self.an.get_attendances_from_event(event):
            yield self.rsvp_class(
                event=self.event_class.from_actionnetwork(event),
                activist=self.activist_class.from_actionnetwork(attendance),
            )
