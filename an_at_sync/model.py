from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Type, TypeVar

if TYPE_CHECKING:
    from .program import Program

from pydantic import BaseModel as PydanticModel

T = TypeVar("T")


class BaseModel(PydanticModel):
    pass


class AirtableTransformerModel(BaseModel):
    @classmethod
    @abstractmethod
    def from_actionnetwork(
        cls: Type[T], source: dict, custom_fields: Optional[dict] = None
    ) -> T:
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


class BaseActivist(AirtableTransformerModel):
    pass


class BaseRSVP(BaseModel):
    """
    Note: Can't use AirtableTransformerModel because
    the base methods don't work for this pivot table.
    """

    activist: BaseActivist
    event: "BaseEvent"

    @abstractmethod
    def id_column(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def activist_column(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def event_column(self) -> str:
        raise NotImplementedError()


class BaseEvent(AirtableTransformerModel):
    rsvps: Optional[List[BaseRSVP]]

    def set_rsvps(self, rsvps: List[BaseRSVP]) -> None:
        self.rsvps = rsvps

    def add_rsvp(self, rsvp: BaseRSVP) -> None:
        if not self.rsvps:
            self.rsvps = []
        self.rsvps.append(rsvp)

    def finalize(self, program: "Program", event) -> Iterable[BaseEvent]:
        self.set_rsvps(list(program._get_rsvps_from_event(event)))
        yield self


BaseRSVP.update_forward_refs()
