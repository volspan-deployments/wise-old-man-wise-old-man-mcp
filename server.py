from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
import threading
from fastmcp import FastMCP
import httpx
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("Wise Old Man")

BASE_URL = "https://api.wiseoldman.net/v2"
API_KEY = os.environ.get("WOM_API_KEY", "")

def get_headers() -> dict:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if API_KEY:
        headers["x-api-key"] = API_KEY
    return headers


@mcp.tool()
async def search_players(query: str, limit: int = 10) -> dict:
    """Search for Old School RuneScape players by username on Wise Old Man. Use this when the user wants to find a player, look up a username, or get player suggestions based on a partial name."""
    params = {"username": query, "limit": limit}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/players/search",
            headers=get_headers(),
            params=params,
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "detail": response.text}
        return {"results": response.json()}


@mcp.tool()
async def get_player(username: str) -> dict:
    """Retrieve detailed profile information for a specific OSRS player including their stats, gains, and achievements. Use this when the user wants to view a player's full profile or stats."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/players/{username}",
            headers=get_headers(),
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "detail": response.text}
        return response.json()


@mcp.tool()
async def get_player_gains(username: str, period: str = "week") -> dict:
    """Fetch the experience and skill gains for a specific player over a given time period. Use this to check how much a player has progressed in skills, bosses, or activities within a timeframe. Valid periods: '5min', 'day', 'week', 'month', 'year'."""
    valid_periods = ["5min", "day", "week", "month", "year"]
    if period not in valid_periods:
        return {"error": f"Invalid period '{period}'. Must be one of: {', '.join(valid_periods)}"}
    params = {"period": period}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/players/{username}/gained",
            headers=get_headers(),
            params=params,
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "detail": response.text}
        return response.json()


@mcp.tool()
async def get_player_achievements(username: str) -> dict:
    """Retrieve the list of achievements unlocked by a specific player, such as milestone levels, boss kills, or collection log completions. Use this when the user asks about a player's accomplishments."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/players/{username}/achievements",
            headers=get_headers(),
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "detail": response.text}
        return {"achievements": response.json()}


@mcp.tool()
async def search_groups(query: str, limit: int = 10) -> dict:
    """Search for clans or groups on Wise Old Man by name. Use this when the user wants to find a group, clan, or team to view their collective stats and competitions."""
    params = {"name": query, "limit": limit}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/groups/search",
            headers=get_headers(),
            params=params,
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "detail": response.text}
        return {"results": response.json()}


@mcp.tool()
async def get_group(group_id: int) -> dict:
    """Retrieve detailed information about a specific group or clan including its members, hiscores, and competitions. Use this when the user wants to explore a group's details or membership."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/groups/{group_id}",
            headers=get_headers(),
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "detail": response.text}
        return response.json()


@mcp.tool()
async def get_competition(competition_id: int) -> dict:
    """Retrieve details about a specific skilling or bossing competition on Wise Old Man, including participants, scores, and the competition timeframe. Use this when the user asks about a particular competition or event."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/competitions/{competition_id}",
            headers=get_headers(),
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "detail": response.text}
        return response.json()


@mcp.tool()
async def update_player(username: str) -> dict:
    """Trigger a manual update/sync of a player's stats from the OSRS hiscores. Use this when a player's data appears outdated or the user explicitly requests a refresh of their stats."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/players/{username}",
            headers=get_headers(),
            timeout=60.0,
        )
        if response.status_code not in (200, 201):
            return {"error": f"API returned status {response.status_code}", "detail": response.text}
        return {"success": True, "player": response.json()}




_SERVER_SLUG = "wise-old-man-wise-old-man"

def _track(tool_name: str, ua: str = ""):
    try:
        import urllib.request, json as _json
        data = _json.dumps({"slug": _SERVER_SLUG, "event": "tool_call", "tool": tool_name, "user_agent": ua}).encode()
        req = urllib.request.Request("https://www.volspan.dev/api/analytics/event", data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=1)
    except Exception:
        pass

async def health(request):
    return JSONResponse({"status": "ok", "server": mcp.name})

async def tools(request):
    registered = await mcp.list_tools()
    tool_list = [{"name": t.name, "description": t.description or ""} for t in registered]
    return JSONResponse({"tools": tool_list, "count": len(tool_list)})

mcp_app = mcp.http_app(transport="streamable-http", stateless_http=True)

class _FixAcceptHeader:
    """Ensure Accept header includes both types FastMCP requires."""
    def __init__(self, app):
        self.app = app
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            accept = headers.get(b"accept", b"").decode()
            if "text/event-stream" not in accept:
                new_headers = [(k, v) for k, v in scope["headers"] if k != b"accept"]
                new_headers.append((b"accept", b"application/json, text/event-stream"))
                scope = dict(scope, headers=new_headers)
        await self.app(scope, receive, send)

app = _FixAcceptHeader(Starlette(
    routes=[
        Route("/health", health),
        Route("/tools", tools),
        Mount("/", mcp_app),
    ],
    lifespan=mcp_app.lifespan,
))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
