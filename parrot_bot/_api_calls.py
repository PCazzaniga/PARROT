"""
Module that contains the necessary for interacting with Twitch API.

Functions:
    set_http_client(x):         Sets x as the http client used to post
    send_chat_message(x, y):    Send x on chat, attempting with maximum backoff of y
"""

import asyncio
import logging
from aiohttp import ClientSession
from ._bot_state import STATE
from ._load_config import BOT_ID, CHANNEL_ID, CLIENT_ID, refresh_auth_token

_http_client: ClientSession | None = None

_SEND_MESSAGE_URL = 'https://api.twitch.tv/helix/chat/messages'
_EVENTSUB_SUB_URL = 'https://api.twitch.tv/helix/eventsub/subscriptions'
_BASE_BACKOFF = 3
_MAX_BACKOFF = 300


class SubscriptionError(Exception):
    pass

def set_http_client(client: ClientSession) -> None:
    global _http_client
    _http_client = client

def _build_auth_headers() -> dict[str, str]:
    return {
        'Authorization': f'Bearer {STATE.auth_token}',
        'Client-Id': CLIENT_ID,
        'Content-Type': 'application/json'
    }

async def _post_with_retry(
    post_reason: str,
    url: str,
    json_content: dict,
    success_statuses: set[int],
    max_backoff: int = _MAX_BACKOFF,
) -> tuple[int, dict | None]:
    """POSTs to url, retrying on transient failures. Returns (status_code, response_body) on success or unrecoverable failure."""
    backoff = _BASE_BACKOFF
    headers = _build_auth_headers()
    # This loop keeps trying to POST until successful, backoff exceeded or unexpected error
    while True:
        async with _http_client.post(url, headers=headers, json=json_content) as response:
            if response.status in success_statuses:
                data = None
                # Wrap to cover success responses that don't actually have a body (.json raises an exception)
                try:
                    data = await response.json()
                except Exception:
                    pass
                return response.status, data
            if response.status in (401, 403):
                # If received an authentication error re-authenticate before retrying next iteration
                logging.error(f"Auth error {response.status} during {post_reason}, re-authenticating")
                STATE.auth_token = await refresh_auth_token()
                headers = _build_auth_headers()
            elif response.status == 429:
                # If asked for a specific backoff wait for that much time before retrying next iteration
                retry_after = int(response.headers.get('Retry-After', backoff))
                logging.warning(f"Rate limited during {post_reason}, retrying in {retry_after}s")
                await asyncio.sleep(retry_after)
            elif 500 <= response.status < 600:
                # If received other server errors wait with exponential backoff before retrying next iteration
                if backoff > max_backoff:
                    data = await response.json()
                    logging.error(f"Failed too many times during {post_reason} (status {response.status}), giving up")
                    logging.debug(data)
                    return response.status, None
                logging.warning(f"Server error {response.status} during {post_reason}, retrying in {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
            else:
                # If received any other error give up
                data = await response.json()
                logging.error(f"Unexpected status {response.status} during {post_reason}, giving up")
                logging.debug(data)
                return response.status, None

async def send_chat_message(chat_message: str, max_backoff: int = _MAX_BACKOFF) -> None:
    jsn = {
        'broadcaster_id': CHANNEL_ID,
        'sender_id': BOT_ID,
        'message': chat_message
    }
    status, _ = await _post_with_retry(
        "message transmission", _SEND_MESSAGE_URL, jsn, success_statuses={200}, max_backoff=max_backoff
    )
    if status == 200:
        logging.info(f"Sent: {chat_message}")

async def register_to_eventsub() -> None:
    jsn = {
        'type': 'channel.chat.message',
        'version': '1',
        'condition': {'broadcaster_user_id': CHANNEL_ID, 'user_id': BOT_ID},
        'transport': {'method': 'websocket', 'session_id': STATE.websocket_session_id}
    }
    status, data = await _post_with_retry(
        "subscription", _EVENTSUB_SUB_URL, jsn, success_statuses={202, 409}, max_backoff=_MAX_BACKOFF // 5
    )
    if status == 202:
        logging.info(f"Subscribed to channel.chat.message [{data['data'][0]['id']}]")
    elif status == 409:
        logging.info("Subscription already exists, continuing")
    else:
        raise SubscriptionError(f"Failed to subscribe to channel.chat.message with status {status}")