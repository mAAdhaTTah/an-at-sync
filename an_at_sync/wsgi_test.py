import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_should_return_success(client: AsyncClient) -> None:
    response = await client.post(url="/api/webhooks/actionnetwork", content="[]")

    assert response.status_code == 200
    assert response.json() == {"success": True}
