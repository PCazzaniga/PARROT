"""
Pydantic models for Twitch EventSub WebSocket messages.

Declares models only for fields that the application uses or cheap fields that might be useful for future features.
All other fields are silently dropped.
"""

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, model_validator


class _Base(BaseModel):
    model_config = ConfigDict(extra='ignore')   # This drops extra fields from the message


# Fragment sub-objects

class Mention(_Base):
    user_id: str
    user_login: str
    user_name: str

class Emote(_Base):
    id: str
    emote_set_id: str
    owner_id: str
    format: list[str]

class Cheermote(_Base):
    prefix: str
    bits: int
    tier: int

class Fragment(_Base):
    type: Literal['text', 'mention', 'emote', 'cheermote']
    text: str
    mention: Mention | None = None
    emote: Emote | None = None
    cheermote: Cheermote | None = None


# Chat event message

class ChatMessage(_Base):
    text: str
    fragments: list[Fragment]

class Badge(_Base):
    set_id: str
    id: str
    info: str

class ChatEvent(_Base):
    broadcaster_user_id: str
    broadcaster_user_login: str
    broadcaster_user_name: str
    chatter_user_id: str
    chatter_user_login: str
    chatter_user_name: str
    message_id: str
    message: ChatMessage
    message_type: str
    color: str
    badges: list[Badge] = []
    # reply, cheer, channel_points and all fields related to shared chat are dropped


# Subscription (revocation)

class Subscription(_Base):
    type: str
    status: str


# Session welcome / reconnect / keepalive

class Session(_Base):
    id: str
    status: str
    keepalive_timeout_seconds: int | None = None
    reconnect_url: str | None = None
    connected_at: datetime | None = None


# Routing layer

class Payload(_Base):
    session: Session | None = None
    event: ChatEvent | None = None
    subscription: Subscription | None = None

class Metadata(_Base):
    message_id: str
    message_type: Literal[
        'session_welcome',
        'session_keepalive',
        'session_reconnect',
        'notification',
        'revocation',
    ]
    message_timestamp: datetime
    subscription_type: str | None = None
    subscription_version: str | None = None


# Top-level container

class MetadataOnly(_Base):
    metadata: Metadata

class EventSubMessage(_Base):
    metadata: Metadata
    payload: Payload

    @model_validator(mode='after')
    def _check_payload_coherence(self) -> 'EventSubMessage':
        t = self.metadata.message_type
        p = self.payload
        if t == 'notification' and p.event is None:
            raise ValueError("notification message is missing payload.event")
        if t == 'revocation' and p.subscription is None:
            raise ValueError("revocation message is missing payload.subscription")
        if t == 'session_reconnect' and (
            p.session is None or p.session.reconnect_url is None
        ):
            raise ValueError("session_reconnect message is missing reconnect_url")
        return self