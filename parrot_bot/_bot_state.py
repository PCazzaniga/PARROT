"""
Module that defines the variables that make up the state informations of the bot

Attributes:
    STATE (_BotState): The state informations of the bot
"""
from dataclasses import dataclass, field
from ._load_config import OAUTH_TOKEN
from ._load_settings import settings

@dataclass
class _BotState:
    websocket_session_id: str = ''                      # ID of the current websocket session
    keepalive_timeout: int = 20                         # Session keepalive time (default 10s interval + 10s grace)
    auth_token: str = OAUTH_TOKEN                       # Most recent app auth token
    word: str = settings.REPLACEMENT_WORD               # Word used to modify messages
    intensity: float = settings.INTENSITY               # Likelihood of modifying elements in messages
    cooldown: int = settings.WAIT_SECONDS               # Time to wait between activations
    interval: int = settings.WAIT_MESSAGES              # Chat messages to wait between activations
    no_target: bool = settings.NOTARGET_MODE            # Ability to target the same user in a row
    vip_ids: set = field(default_factory=lambda: set(settings.VIP_IDS))         # Special users tha can use commands
    ignore_ids: set = field(default_factory=lambda: set(settings.IGNORED_IDS))  # Users whose messages can't be modified
    adapt_word: bool = not settings.ADVANCED_MODE       # Replacement mode choice
    max_msg_length: int = settings.MAX_TARGET_LENGTH    # Maximum length for modifiable messages
    last_active: float = 0.0                            # Time of last activation
    wait_messages: int = 0                              # Number of messages waited since last activation
    last_target: str = ''                               # Tracks the sender of the last modified message
    last_reception_time: float = 0.0                    # Used to track keepalive time
    is_first_connection: bool = True                    # Used to distinguis first connection from reconnections
    shutdown: bool = False                              # Bot is shutting down

STATE = _BotState()