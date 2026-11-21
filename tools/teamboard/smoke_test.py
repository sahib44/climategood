# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["mcp>=1.9,<2", "httpx>=0.27"]
# ///
"""End-to-end check against a running board: two fake teammates talk over real MCP.

    uv run tools/teamboard/smoke_test.py <base-url> <token>
"""

import asyncio
import sys
import uuid

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def call(base, token, user, tool, **args):
    headers = {"Authorization": f"Bearer {token}", "X-Teamboard-User": user}
    async with streamablehttp_client(f"{base}/mcp", headers=headers) as (r, w, _):
        async with ClientSession(r, w) as s:
            await s.initialize()
            res = await s.call_tool(tool, args)
            return res.content[0].text


async def main(base, token):
    a, b = f"smoke-a-{uuid.uuid4().hex[:4]}", f"smoke-b-{uuid.uuid4().hex[:4]}"
    print(await call(base, token, a, "post", body="hello from A", topic="test"))
    print(await call(base, token, b, "inbox"))
    out = await call(base, token, b, "inbox")
    assert "No new messages" in out, out
    print(await call(base, token, a, "claim_files", paths=["frontend/src/App.jsx"]))
    out = await call(base, token, b, "claim_files", paths=["frontend/src/App.jsx"])
    assert "held by" in out, out
    print(out)
    await call(base, token, a, "release_files")
    print(await call(base, token, a, "post", body="direct to B", to=b))
    r = httpx.get(f"{base}/unread", params={"user": b}, headers={"Authorization": f"Bearer {token}"})
    assert "direct to B" in r.text, r.text
    r = httpx.get(f"{base}/unread", params={"user": b})
    assert r.status_code == 401, r.status_code
    print("SMOKE TEST PASSED")


asyncio.run(main(sys.argv[1].rstrip("/"), sys.argv[2]))
