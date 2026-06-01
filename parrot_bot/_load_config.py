"""
Module for loading configuration data and refreshing auth tokens.

Attributes:
    BOT_ID (int):       ID of the chatbot's Twitch account
    CLIENT_ID (str):    Client ID of the chatbot application
    CHANNEL_ID (int):   ID of the broadcasting channel's Twitch account
    OAUTH_TOKEN (str):  Most recent authorization token

Functions:
    refresh_auth_token(): Refreshes OAuth token and returns it, also saving it back in the configuration file

Exceptions:
    AuthTokenError: Raised on errors when fetching, refreshing or saving the oauth token
"""

import aiohttp
import asyncio
from aiohttp import web
from datetime import datetime, timedelta
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, field_serializer

class AuthTokenError(Exception):
    pass

class _AppOAuthToken(BaseModel):
    TOKEN: str | None = None
    REFRESH_TOKEN: str | None = None
    EXPIRES_AT: datetime | None = None
    FETCHED : datetime | None = None

    @field_validator("EXPIRES_AT", "FETCHED", mode="before")
    @classmethod
    def parse_rfc1123_datetime(cls, value: str) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        return datetime.strptime(value, "%a, %d %b %Y %H:%M:%S GMT")    # Example: "Fri, 17 Jan 2025 13:45:03 GMT"
    
    @field_serializer("EXPIRES_AT", "FETCHED")
    def serialize_datetime(self, value: datetime) -> str:
        # Custom serializer, so that when dumping to json it gets formatted as RFC 1123 rather than ISO 8601
        return value.strftime("%a, %d %b %Y %H:%M:%S GMT")

class Config(BaseModel):
    BOT_ACCOUNT_ID: int = Field(..., gt=0)
    APP_CLIENT_ID: str = Field(...)
    APP_CLIENT_SECRET: str = Field(...)     # Client secret of the chatbot application
    CHANNEL_ACCOUNT_ID: int = Field(..., gt=0)
    APP_OAUTH_TOKEN: _AppOAuthToken = Field(...)

_CONFIG_FILE = Path(__file__).parent / "PRIVATE_config.json"    # File that contains the configuration data
_MAX_BACKOFF = 16                       # Maximum backoff time when fetching auth tokens

# The with block ensures resources are closed properly automatically
with open(_CONFIG_FILE) as config_file:
     _CONFIG = Config.model_validate_json(config_file.read())

async def _is_valid_token(token: str) -> bool:
    """Checks if the token is valid and not expired."""
    # First, quick checks on expiration
    if _CONFIG.APP_OAUTH_TOKEN.EXPIRES_AT is None:
        return False
    if datetime.utcnow() >= _CONFIG.APP_OAUTH_TOKEN.EXPIRES_AT:
        return False
    # Then request validation (response 200 -> valid, 401 -> not valid)
    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://id.twitch.tv/oauth2/validate",
            headers={'Authorization': f'OAuth {token}'},
            timeout=aiohttp.ClientTimeout(total=10, connect=3)
        ) as response:
            return response.status == 200

def _save_token(token: str, refresh_token: str, expires_in: int) -> None:
    """Saves the token data back to the config file."""
    fetched = datetime.utcnow()
    _CONFIG.APP_OAUTH_TOKEN = _AppOAuthToken(
        TOKEN=token,
        REFRESH_TOKEN=refresh_token,
        EXPIRES_AT=fetched + timedelta(seconds=expires_in),
        FETCHED=fetched,
    )
    try:
        with open(_CONFIG_FILE, "w") as config_file:
            config_file.write(_CONFIG.model_dump_json(indent=2))
    except OSError as e:
        raise AuthTokenError(f"Failed to save token data to '{_CONFIG_FILE}' with error: {e}")

async def _initial_authorization() -> str:
    """Starts a temporary local server to handle initial manual OAuth authorization."""
    url = (
        "https://id.twitch.tv/oauth2/authorize"
        "?response_type=code"
        f"&client_id={_CONFIG.APP_CLIENT_ID}"
        "&redirect_uri=http://localhost:3000/callback"
        "&scope=user:bot+user:read:chat+user:write:chat"    # Required authorizations for the bot application
    )
    print(f"Set up required.\nOpen this URL in a browser while logged in as the bot account:\n\n{url}\n")

    # This is a Future, to bridge its await call with the callback (fired only when the user authorizes in browser)
    token_future: asyncio.Future[str] = asyncio.get_running_loop().create_future()

    async def handle_callback(request: web.Request) -> web.Response:
        code = request.rel_url.query.get("code")
        if not code:
            token_future.set_exception(AuthTokenError("No code received in OAuth callback"))
            return web.Response(text="Authorization failed, no code received.")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://id.twitch.tv/oauth2/token",
                params={
                    "client_id": _CONFIG.APP_CLIENT_ID,
                    "client_secret": _CONFIG.APP_CLIENT_SECRET,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": "http://localhost:3000/callback",
                },
                timeout=aiohttp.ClientTimeout(total=10, connect=3),
            ) as response:
                if response.status >= 400:
                    token_future.set_exception(AuthTokenError(f"Token exchange failed (status {response.status})"))
                    return web.Response(text="Authorization failed, token exchange error.")
                data = await response.json()
        _save_token(data["access_token"], data["refresh_token"], data["expires_in"])
        if not token_future.done():
            token_future.set_result(data["access_token"])
        return web.Response(text="Authorization successful, you can close this tab.")

    # Start a temporary local web application with AppRunner + TCPSite to get user to authorize
    app = web.Application()
    app.router.add_get("/callback", handle_callback)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", 3000)
    await site.start()
    try:
        return await token_future
    finally:
        await runner.cleanup()

async def refresh_auth_token() -> str:
    """Refreshes the OAuth app token from Twitch, retrying with exponential backoff on failures. On success saves and returns it."""
    backoff = 2
    # Use Authorization Code flow to automatically refresh token
    async with aiohttp.ClientSession() as session:
        # This loop requests a new token, retrying on 4xx or 5xx responses until maximum backoff (2, 4, 8, 16 -> 5 attempts over ~30s)
        while True:
            async with session.post(
                "https://id.twitch.tv/oauth2/token",
                params={
                    "client_id": _CONFIG.APP_CLIENT_ID,
                    "client_secret": _CONFIG.APP_CLIENT_SECRET,
                    "refresh_token": _CONFIG.APP_OAUTH_TOKEN.REFRESH_TOKEN,
                    "grant_type": "refresh_token",
                },
                timeout=aiohttp.ClientTimeout(total=10, connect=3),
            ) as response:
                if response.status < 400:
                    data = await response.json()
                    _save_token(data["access_token"], data["refresh_token"], data["expires_in"])
                    return data["access_token"]
                if backoff > _MAX_BACKOFF:
                    raise AuthTokenError(f"Failed too many times to refresh auth token (status {response.status})")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF)

async def _get_initial_token() -> str:
    """Returns the auth token from the config file if it's still valid, otherwise refreshes it.
    If there is no token in the file starts manual initialization procedure."""
    token = _CONFIG.APP_OAUTH_TOKEN.TOKEN
    if not token:
        return await _initial_authorization()
    return token if await _is_valid_token(token) else await refresh_auth_token()

BOT_ID = str(_CONFIG.BOT_ACCOUNT_ID)    # Cast to string for comparisons
CLIENT_ID = _CONFIG.APP_CLIENT_ID
CHANNEL_ID = str(_CONFIG.CHANNEL_ACCOUNT_ID)    # Cast to string because EventSub API wants it as a string
OAUTH_TOKEN = asyncio.run(_get_initial_token())