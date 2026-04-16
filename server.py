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

mcp = FastMCP("Wise Old Man API")

BASE_URL = "https://api.wiseoldman.net/v2"
API_KEY = os.environ.get("WISE_OLD_MAN_API_KEY", "")

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
    """Search for Old School RuneScape players by username on Wise Old Man. Use this when a user wants to find a player, look up someone's stats, or get player suggestions based on a partial username."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/players/search",
            headers=get_headers(),
            params={"username": query, "limit": limit},
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "details": response.text}
        return {"results": response.json()}


@mcp.tool()
async def get_player(username: str) -> dict:
    """Retrieve detailed stats, skills, and progress information for a specific Old School RuneScape player by their username. Use this when a user wants to view a player's current stats, levels, or overall profile."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/players/{username}",
            headers=get_headers(),
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "details": response.text}
        return response.json()


@mcp.tool()
async def update_player(username: str) -> dict:
    """Trigger a stats update for a specific player by syncing with the OSRS hiscores. Use this when a user wants to refresh or update a player's tracked data to reflect recent in-game progress."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/players/{username}",
            headers=get_headers(),
            timeout=60.0,
        )
        if response.status_code not in (200, 201):
            return {"error": f"API returned status {response.status_code}", "details": response.text}
        return {"success": True, "player": response.json()}


@mcp.tool()
async def get_player_gains(username: str, period: str = "week") -> dict:
    """Retrieve experience gains and progress over a specific time period for a player. Use this when a user wants to see how much a player has gained in skills or overall XP over a day, week, or month. Period options: 'day', 'week', 'month', 'year', 'five_years'."""
    valid_periods = ["day", "week", "month", "year", "five_years"]
    if period not in valid_periods:
        return {"error": f"Invalid period '{period}'. Must be one of: {', '.join(valid_periods)}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/players/{username}/gained",
            headers=get_headers(),
            params={"period": period},
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "details": response.text}
        return response.json()


@mcp.tool()
async def search_groups(query: str, limit: int = 10) -> dict:
    """Search for player groups or clans on Wise Old Man by name. Use this when a user wants to find a group, clan, or community to view their competitions, members, or hiscores."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/groups/search",
            headers=get_headers(),
            params={"name": query, "limit": limit},
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "details": response.text}
        return {"results": response.json()}


@mcp.tool()
async def get_group(group_id: int) -> dict:
    """Retrieve detailed information about a specific group or clan including its members, hiscores, and recent activity. Use this when a user wants to explore a group's statistics, member list, or group-level achievements."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/groups/{group_id}",
            headers=get_headers(),
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "details": response.text}
        return response.json()


@mcp.tool()
async def get_competition(competition_id: int) -> dict:
    """Retrieve details about a specific competition including participants, scores, and duration. Use this when a user wants to view competition results, leaderboards, or check who is winning a specific event."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/competitions/{competition_id}",
            headers=get_headers(),
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "details": response.text}
        return response.json()


@mcp.tool()
async def get_player_achievements(username: str) -> dict:
    """Retrieve all achievements unlocked by a specific player, such as milestone levels, boss kill counts, or skill thresholds. Use this when a user wants to see what accomplishments a player has earned or is close to earning."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/players/{username}/achievements",
            headers=get_headers(),
            timeout=30.0,
        )
        if response.status_code != 200:
            return {"error": f"API returned status {response.status_code}", "details": response.text}
        return {"achievements": response.json()}




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

sse_app = mcp.http_app(transport="sse")

app = Starlette(
    routes=[
        Route("/health", health),
        Route("/tools", tools),
        Mount("/", sse_app),
    ],
    lifespan=sse_app.lifespan,
)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
