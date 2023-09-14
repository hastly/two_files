from uuid import UUID

from srv.run import create_app


async def test_hello(aiohttp_client):
    client = await aiohttp_client(create_app())
    resp = await client.post("/upload/")
    assert resp.status == 200
    text = await resp.text()
    assert UUID(text)
