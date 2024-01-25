from __future__ import annotations

from abc import abstractmethod
from typing import Any, Dict, Generic, Iterable, List, Optional, Type, TypeVar, Union

from pyairtable import Table
from pyairtable.formulas import match
from pydantic import BaseModel as PydanticModel
from pydantic import ValidationError

from an_at_sync.actionnetwork import ActionNetworkApi

T = TypeVar("T", bound="BaseModel")


class BaseModel(PydanticModel):
    @classmethod
    @abstractmethod
    def from_actionnetwork(cls: Type[T], source: dict, **kwargs: Any) -> T:
        raise NotImplementedError()

    @abstractmethod
    def display_name(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def pk(self) -> Dict:
        raise NotImplementedError()

    @abstractmethod
    def to_airtable(self) -> dict:
        raise NotImplementedError()

    def __str__(self):
        params = ", ".join(
            [f"{key}={value}" for key, value in self.to_airtable().items()]
        )
        return f"<{self.__class__.__name__} {params}>"


class BaseActivist(BaseModel):
    pass


class BaseRSVP(BaseModel):
    activist: BaseActivist
    event: "BaseEvent"

    @abstractmethod
    def activist_column(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def event_column(self) -> str:
        raise NotImplementedError()


class BaseEvent(BaseModel):
    pass


BaseRSVP.update_forward_refs()

M = TypeVar("M", bound="BaseModel")
KOD = TypeVar("KOD")
VOD = TypeVar("VOD")


class ObjectDict(Generic[KOD, VOD]):
    """
    This is obviously missing a lot to be a full-fledged dict
    but this works for what we want to do for now.
    """

    def __init__(self) -> None:
        self.keys: List[KOD] = []
        self.values: List[VOD] = []

    def __setitem__(self, key, val):
        for i, existing_key in enumerate(self.keys):
            if existing_key == key:
                self.values[i] = val
        else:
            self.keys.append(key)
            self.values.append(val)

    def get(self, key) -> Optional[VOD]:
        for i, existing_key in enumerate(self.keys):
            if existing_key == key:
                return self.values[i]

        return None

    def __repr__(self):
        return f"<ObjectDict keys={str(self.keys)} values={str(self.values)}>"


class BaseRepository(Generic[M]):
    def __init__(self, an: ActionNetworkApi, at: Table, klass: Type[M]) -> None:
        self.an = an
        self.at = at
        self.klass = klass
        self.model_to_at = ObjectDict[M, dict]()
        self.at_to_model = ObjectDict[dict, M]()
        self.model_to_an = ObjectDict[M, dict]()
        self.an_to_model = ObjectDict[dict, M]()

    def get_airtable_record(self, model: M):
        at_model = self.model_to_at.get(model)
        if not at_model:
            at_model = self.at.first(formula=match(model.pk()))
            if at_model:
                self._associate_model(model, at_model=at_model)
        return at_model

    def insert_airtable_record(self, model: M, **kwargs):
        return self.at.create(model.to_airtable())

    def update_airtable_record(self, model: M):
        airtable_record = self.get_airtable_record(model)
        if airtable_record is None:
            raise Exception("Cannot update record that does not exist")
        return self.at.update(airtable_record["id"], model.to_airtable())

    def should_update_airtable_record(self, model: M):
        airtable_record = self.get_airtable_record(model)
        if airtable_record is None:
            raise Exception("Cannot update record that does not exist")
        fields = airtable_record["fields"]
        update = model.to_airtable()

        def empty_str_to_none(val):
            return None if val == "" else val

        # Handle situations where an empty string on the AN side maps
        # to None on the AT side, such that an update would produce
        # no changes but this would otherwise mark them as different
        return {key: empty_str_to_none(update.get(key)) for key in update} != {
            key: empty_str_to_none(fields.get(key)) for key in update
        }

    def from_actionnetwork_url(self, url: str, **kwargs) -> M:
        an_model = self.an.session.get(url).json()
        model = self.an_to_model.get(an_model)
        if not model:
            model = self.klass.from_actionnetwork(an_model, **kwargs)
            self._associate_model(model, an_model=an_model)
        return model

    def _associate_model(
        self,
        model: M,
        *,
        an_model: Optional[dict] = None,
        at_model: Optional[dict] = None,
    ):
        if an_model:
            self.an_to_model[an_model] = model
            self.model_to_an[model] = an_model

        if at_model:
            self.at_to_model[at_model] = model
            self.model_to_at[model] = at_model


class EventRepository(BaseRepository[BaseEvent]):
    def all_from_actionnetwork(self) -> Iterable[Union[BaseEvent, ValidationError]]:
        for an_event in self.an.get_all_events():
            try:
                event = self.an_to_model.get(an_event)
                if not event:
                    event = self.klass.from_actionnetwork(an_event)
                    self._associate_model(event, an_model=an_event)
                yield event
            except ValidationError as e:
                yield e

        for an_event in self.an.get_all_events_from_event_campaigns():
            try:
                event = self.an_to_model.get(an_event)
                if not event:
                    event = self.klass.from_actionnetwork(an_event)
                    self._associate_model(event, an_model=an_event)
                yield event
            except ValidationError as e:
                yield e


class ActivistRepository(BaseRepository[BaseActivist]):
    def all_from_actionnetwork(self) -> Iterable[BaseActivist]:
        for an_activist in self.an.get_all_activists():
            activist = self.an_to_model.get(an_activist)
            if not activist:
                activist = self.klass.from_actionnetwork(an_activist)
                self._associate_model(activist, an_model=an_activist)
            yield activist


class RSVPRepository(BaseRepository[BaseRSVP]):
    def insert_airtable_record(self, model: BaseRSVP, **kwargs):
        return self.at.create(
            {
                **model.to_airtable(),
                model.activist_column(): [kwargs["activist_record"]["id"]],
                model.event_column(): [kwargs["event_record"]["id"]],
            }
        )

    def from_actionnetwork_for_event(
        self, event: BaseEvent, events: EventRepository, activists: ActivistRepository
    ) -> Iterable[BaseRSVP]:
        an_event = events.model_to_an.get(event)
        if an_event is None:
            raise Exception(
                "Event passed to RSVPRepository#from_actionnetwork_for_event was not loaded from AN;"
                "Loading from AN for AT source not yet supported"
            )

        for an_attendance in self.an.get_attendances_from_event(an_event):
            person_url = an_attendance["_links"]["osdi:person"]["href"]
            activist = activists.from_actionnetwork_url(person_url)
            yield self.klass.from_actionnetwork(
                an_attendance,
                event=event,
                activist=activist,
                event_record=events.get_airtable_record(event)
                or events.insert_airtable_record(event),
                activist_record=activists.get_airtable_record(activist)
                or activists.insert_airtable_record(activist),
            )
