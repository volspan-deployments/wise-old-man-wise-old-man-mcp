from starlette.applications import Starlette
from starlette.routing import Route, Mount
from starlette.responses import JSONResponse
import uvicorn
import threading
from fastmcp import FastMCP
import httpx
import os
from typing import Optional

mcp = FastMCP("Wise Old Man API")

BASE_URL = "https://api.wiseoldman.net/v2"
WOM_BASE_URL = "https://wiseoldman.net"

API_KEY = os.environ.get("WOM_API_KEY", "")

# In-memory store for recent searches (session-based)
_recent_searches: list[str] = []


def get_headers() -> dict:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "WOM-MCP-Server/1.0",
    }
    if API_KEY:
        headers["x-api-key"] = API_KEY
    return headers


@mcp.tool()
async def search_players(query: str) -> dict:
    """Search for Old School RuneScape players on Wise Old Man by username.
    Use this when the user wants to find a player, look up stats, or get
    information about a specific OSRS account. The query is automatically
    trimmed and lowercased."""
    normalized_query = query.strip().lower()
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/players/search",
                params={"username": normalized_query},
                headers=get_headers(),
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
            # Store in recent searches
            if normalized_query and normalized_query not in _recent_searches:
                _recent_searches.insert(0, normalized_query)
                if len(_recent_searches) > 20:
                    _recent_searches.pop()
            return {
                "success": True,
                "query": normalized_query,
                "results": data,
                "count": len(data) if isinstance(data, list) else 1,
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "query": normalized_query,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            return {
                "success": False,
                "query": normalized_query,
                "error": str(e),
            }


@mcp.tool()
async def search_groups(query: str) -> dict:
    """Search for groups on Wise Old Man by name. Use this when the user wants
    to find a clan, team, or group to view their competitions, members, or
    group hiscores."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/groups/search",
                params={"name": query.strip()},
                headers=get_headers(),
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
            # Store in recent searches
            normalized = query.strip().lower()
            if normalized and normalized not in _recent_searches:
                _recent_searches.insert(0, normalized)
                if len(_recent_searches) > 20:
                    _recent_searches.pop()
            return {
                "success": True,
                "query": query.strip(),
                "results": data,
                "count": len(data) if isinstance(data, list) else 1,
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "query": query.strip(),
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            return {
                "success": False,
                "query": query.strip(),
                "error": str(e),
            }


@mcp.tool()
async def upload_profile_image(image_path: str) -> dict:
    """Upload a profile avatar image for a Wise Old Man player or group profile.
    The image is automatically resized and compressed to 120x120 pixels before
    being stored. Use this when the user wants to set or update a profile picture."""
    if not os.path.exists(image_path):
        return {
            "success": False,
            "error": f"File not found: {image_path}",
        }
    async with httpx.AsyncClient() as client:
        try:
            with open(image_path, "rb") as f:
                file_content = f.read()
            filename = os.path.basename(image_path)
            files = {"profileImage": (filename, file_content)}
            headers = {}
            if API_KEY:
                headers["x-api-key"] = API_KEY
            response = await client.post(
                f"{BASE_URL}/upload/profile-image",
                files=files,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return {
                "success": True,
                "message": "Profile image uploaded successfully (resized to 120x120)",
                "response": response.json() if response.content else {},
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


@mcp.tool()
async def upload_banner_image(image_path: str) -> dict:
    """Upload a banner image for a Wise Old Man group or profile page. The image
    is automatically resized and compressed to 1184x144 pixels before being stored.
    Use this when the user wants to set or update a profile or group banner."""
    if not os.path.exists(image_path):
        return {
            "success": False,
            "error": f"File not found: {image_path}",
        }
    async with httpx.AsyncClient() as client:
        try:
            with open(image_path, "rb") as f:
                file_content = f.read()
            filename = os.path.basename(image_path)
            files = {"bannerImage": (filename, file_content)}
            headers = {}
            if API_KEY:
                headers["x-api-key"] = API_KEY
            response = await client.post(
                f"{BASE_URL}/upload/banner-image",
                files=files,
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return {
                "success": True,
                "message": "Banner image uploaded successfully (resized to 1184x144)",
                "response": response.json() if response.content else {},
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


@mcp.tool()
async def get_player_gains(username: str) -> dict:
    """Navigate to or retrieve the gains page for a specific OSRS player.
    Use this when the user wants to see how much XP or stats a player has
    gained over a period. Supports the RuneLite plugin redirect format."""
    normalized_username = username.strip().lower()
    gains_url = f"{WOM_BASE_URL}/players/{normalized_username}/gained"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{BASE_URL}/players/{normalized_username}",
                headers=get_headers(),
                timeout=15.0,
            )
            response.raise_for_status()
            player_data = response.json()
            return {
                "success": True,
                "username": normalized_username,
                "gains_page_url": gains_url,
                "player_info": player_data,
                "message": f"View gains for {username} at: {gains_url}",
            }
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return {
                    "success": False,
                    "username": normalized_username,
                    "gains_page_url": gains_url,
                    "error": f"Player '{username}' not found on Wise Old Man. They may need to be tracked first.",
                    "suggestion": f"Visit {gains_url} to add them.",
                }
            return {
                "success": False,
                "username": normalized_username,
                "gains_page_url": gains_url,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
            }
        except Exception as e:
            return {
                "success": False,
                "username": normalized_username,
                "gains_page_url": gains_url,
                "error": str(e),
            }


@mcp.tool()
async def get_community_links(resource: str) -> dict:
    """Retrieve official Wise Old Man community and resource links including
    GitHub, Discord, Twitter/X, Patreon, API documentation, and country flag
    setup guide. Use this when the user asks how to contribute, join the
    community, support the project, or access the API docs."""
    links = {
        "github": {
            "url": "https://github.com/wise-old-man/wise-old-man",
            "description": "Wise Old Man GitHub repository - contribute to the open source project",
            "redirect": f"{WOM_BASE_URL}/github",
        },
        "discord": {
            "url": "https://discordapp.com/invite/Ky5vNt2",
            "description": "Join the Wise Old Man Discord community server",
            "redirect": f"{WOM_BASE_URL}/discord",
        },
        "twitter": {
            "url": "https://twitter.com/RubenPsikoi",
            "description": "Follow RubenPsikoi on Twitter/X for updates",
            "redirect": f"{WOM_BASE_URL}/twitter",
        },
        "patreon": {
            "url": "https://patreon.com/wiseoldman",
            "description": "Support Wise Old Man on Patreon",
            "redirect": f"{WOM_BASE_URL}/patreon",
        },
        "docs": {
            "url": "https://docs.wiseoldman.net",
            "description": "Wise Old Man API documentation for developers",
            "redirect": f"{WOM_BASE_URL}/docs",
        },
        "flags": {
            "url": "https://github.com/wise-old-man/wise-old-man/wiki/User-Guide:-How-to-setup-countries-flags",
            "description": "Guide for setting up country flags on your Wise Old Man profile",
            "redirect": f"{WOM_BASE_URL}/flags",
        },
    }
    resource_lower = resource.strip().lower()
    if resource_lower not in links:
        return {
            "success": False,
            "error": f"Unknown resource '{resource}'. Available resources: {', '.join(links.keys())}",
            "available_resources": list(links.keys()),
        }
    link_info = links[resource_lower]
    return {
        "success": True,
        "resource": resource_lower,
        "url": link_info["url"],
        "description": link_info["description"],
        "redirect_url": link_info["redirect"],
        "all_links": {k: v["url"] for k, v in links.items()},
    }


@mcp.tool()
async def get_leaderboards(
    leaderboard_type: str = "top",
    game_mode: Optional[str] = "main",
) -> dict:
    """Navigate to or retrieve Wise Old Man leaderboard pages. Use this when
    the user wants to view top players, EHP (Efficient Hours Played) leaderboards,
    or EHB (Efficient Hours Bossed) leaderboards for a specific game mode."""
    leaderboard_type = leaderboard_type.strip().lower()
    valid_types = ["top", "ehp", "ehb"]
    if leaderboard_type not in valid_types:
        return {
            "success": False,
            "error": f"Invalid leaderboard_type '{leaderboard_type}'. Must be one of: {', '.join(valid_types)}",
        }
    valid_modes = ["main", "ironman", "ultimate", "hardcore", "seasonal", "tournament", "fresh_start", "skiller", "1def"]
    gm = (game_mode or "main").strip().lower()
    if leaderboard_type == "top":
        page_url = f"{WOM_BASE_URL}/leaderboards/top"
        api_endpoint = f"{BASE_URL}/efficiency/leaderboard"
        params = {"metric": "ehp", "type": "skilling"}
    elif leaderboard_type == "ehp":
        page_url = f"{WOM_BASE_URL}/ehp/{gm}"
        api_endpoint = f"{BASE_URL}/efficiency/leaderboard"
        params = {"metric": "ehp", "playerType": gm if gm != "main" else None}
    else:  # ehb
        page_url = f"{WOM_BASE_URL}/ehb/{gm}"
        api_endpoint = f"{BASE_URL}/efficiency/leaderboard"
        params = {"metric": "ehb", "playerType": gm if gm != "main" else None}
    # Remove None values
    params = {k: v for k, v in params.items() if v is not None}
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                api_endpoint,
                params=params,
                headers=get_headers(),
                timeout=15.0,
            )
            response.raise_for_status()
            data = response.json()
            return {
                "success": True,
                "leaderboard_type": leaderboard_type,
                "game_mode": gm,
                "page_url": page_url,
                "results": data,
                "count": len(data) if isinstance(data, list) else 1,
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "leaderboard_type": leaderboard_type,
                "game_mode": gm,
                "page_url": page_url,
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "message": f"You can view this leaderboard directly at: {page_url}",
            }
        except Exception as e:
            return {
                "success": False,
                "leaderboard_type": leaderboard_type,
                "game_mode": gm,
                "page_url": page_url,
                "error": str(e),
                "message": f"You can view this leaderboard directly at: {page_url}",
            }


@mcp.tool()
async def get_recent_searches(
    action: str = "list",
    term: Optional[str] = None,
) -> dict:
    """Retrieve the list of recent player or group searches stored locally for
    the current user session. Use this when the user wants to revisit a previously
    searched player or group, or to manage their search history by clearing or
    removing entries."""
    global _recent_searches
    action = action.strip().lower()
    if action == "list":
        return {
            "success": True,
            "action": "list",
            "recent_searches": _recent_searches.copy(),
            "count": len(_recent_searches),
        }
    elif action == "clear":
        _recent_searches.clear()
        return {
            "success": True,
            "action": "clear",
            "message": "All recent searches have been cleared.",
            "recent_searches": [],
            "count": 0,
        }
    elif term:
        normalized_term = term.strip().lower()
        if normalized_term in _recent_searches:
            _recent_searches.remove(normalized_term)
            return {
                "success": True,
                "action": "remove",
                "term": normalized_term,
                "message": f"'{normalized_term}' removed from recent searches.",
                "recent_searches": _recent_searches.copy(),
                "count": len(_recent_searches),
            }
        else:
            return {
                "success": False,
                "action": "remove",
                "term": normalized_term,
                "error": f"'{normalized_term}' not found in recent searches.",
                "recent_searches": _recent_searches.copy(),
            }
    else:
        return {
            "success": False,
            "error": f"Unknown action '{action}'. Use 'list', 'clear', or provide a 'term' to remove.",
            "available_actions": ["list", "clear"],
        }




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
