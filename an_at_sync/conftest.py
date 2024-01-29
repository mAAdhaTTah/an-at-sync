from typing import AsyncGenerator

import pytest
from httpx import AsyncClient

import an_at_sync.program as program


class MockActivist:
    pass


class MockEvent:
    pass


class MockRSVP:
    pass


class MockProgramSettings:
    an_at_sync_activist_model = MockActivist
    an_at_sync_event_model = MockEvent
    an_at_sync_rsvp_model = MockRSVP
    an_api_key = "an_api_key"
    at_base = "at_base"
    at_activists_table = "at_activists_table"
    at_events_table = "at_events_table"
    at_rsvp_table = "at_rsvp_table"
    at_api_key = "at_api_key"


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    from an_at_sync.wsgi import wsgi

    async with AsyncClient(app=wsgi, base_url="http://test") as client:
        yield client


@pytest.fixture(autouse=True)
def env_vars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(program, "ProgramSettings", MockProgramSettings)
