import aiohttp
import asyncio
import logging
import signal
import sys
import time
import websockets
from pydantic import ValidationError
from ._api_calls import send_chat_message, register_to_eventsub, SubscriptionError, set_http_client
from ._bot_state import STATE
from ._commands_settings import (
    DEFAULT_MSG, ERR_MSG, STARTUP_MSG, COMMANDS_LIST, ADVANCED_CMD, IGNORE_CMD, INTENSITY_CMD, INTERVAL_CMD,
    KEYWORD_CMD, LENGTH_CMD, NOTARGET_CMD, TIMER_CMD, TRYOUT_CMD, TURNOFF_CMD, UNIGNORE_CMD, UNVIP_CMD, VIP_CMD
)
from ._EventSub_models import EventSubMessage, MetadataOnly, ChatEvent, ChatMessage
from ._load_config import BOT_ID, AuthTokenError
from ._load_settings import settings, save_settings, SettingsSaveError
from ._replacing import has_replaceable_elements, replace_elements

_EVENTSUB_WEBSOCKET_URL = 'wss://eventsub.wss.twitch.tv/ws'
_BASE_BACKOFF = 3
_MAX_BACKOFF = 300
_MINIMUM_INTERVAL = 5
_MINIMUM_TIMEOUT = 30
_MINIMUM_MAX_LENGTH = 30

_console_log_handler = None


class _GracefulReconnect(Exception):
    def __init__(self, temp_url):
        self.temp_url = temp_url


######## Helpers ########

##### THIS IS CURRENTLY DEPRECATED (kept for reference)#####
#def _dict_to_obj(d):
#    """Converts a raw Dict, such as from json.loads, into a dottable namespace object"""
#    if isinstance(d, dict):
#        return types.SimpleNamespace(**{(k if k.isidentifier() else f'_{k}'): _dict_to_obj(v) for k, v in d.items()})
#    if isinstance(d, list):
#        return [_dict_to_obj(i) for i in d]
#    return d

def _initiate_shutdown(reason: str) -> None:
    """Initiates graceful shutdown"""
    logging.info(f"Shutting down: {reason}")
    STATE.shutdown = True

def _setup_signal_handlers() -> None:
    """Sets up the handlers for stop signals (except SIGKILL, which is considered abnormal termination)"""
    try:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, _initiate_shutdown, "received signal SIGINT")
        loop.add_signal_handler(signal.SIGTERM, _initiate_shutdown, "received signal SIGTERM")
    except NotImplementedError:
        # add_signal_handler is safer but Unix-only, on Windows must fall back to signal.signal
        signal.signal(signal.SIGINT, lambda s, f: _initiate_shutdown("received signal SIGINT"))
        signal.signal(signal.SIGTERM, lambda s, f: _initiate_shutdown("received signal SIGTERM"))

######## Commands handling ########

def _has_mention_parameter(message: ChatMessage) -> bool:
    """Checks that the command message has a @mention after the command name"""
    return len(message.fragments) >= 3 and message.fragments[2].type == 'mention'

def _get_help_msg(command: list[str]) -> str:
    """Returns the help message associated to the requested command"""
    if len(command) <= 1:
        return ERR_MSG
    match command[1]:
        case '!commands' | '!help':
            return COMMANDS_LIST.help_msg
        case '!advanced':
            return ADVANCED_CMD.help_msg
        case '!ignore':
            return IGNORE_CMD.help_msg
        case '!intensity':
            return INTENSITY_CMD.help_msg
        case '!interval': 
            return INTERVAL_CMD.help_msg
        case '!keyword':
            return KEYWORD_CMD.help_msg + STATE.word + "."
        case '!length':
            return LENGTH_CMD.help_msg
        case '!notarget':
            return NOTARGET_CMD.help_msg
        case '!timer':
            return TIMER_CMD.help_msg
        case '!try':
            return TRYOUT_CMD.help_msg
        case '!turnoff':
            return TURNOFF_CMD.help_msg
        case '!unignore':
            return UNIGNORE_CMD.help_msg
        case '!unvip':
            return UNVIP_CMD.help_msg
        case '!vip':
            return VIP_CMD.help_msg
        case _:
            return DEFAULT_MSG

async def _execute_command(message: ChatMessage) -> None:
    command = message.fragments[1].text.split()
    if command[0] == '!help':
        await send_chat_message(_get_help_msg(command), 60)
        return
    msg = DEFAULT_MSG
    match command[0]:
        case '!commands':
            # Send the commands list
            msg = COMMANDS_LIST.msg
        case '!advanced':
            # Switch replacement mode and send notification
            STATE.adapt_word = not STATE.adapt_word
            msg = ADVANCED_CMD.msg + ("ON" if not STATE.adapt_word else "OFF") + "."
        case '!ignore':
            # Add user to ignore and send notification, or send error if no @user
            if _has_mention_parameter(message):
                mention = message.fragments[2].mention
                STATE.ignore_ids.add(mention.user_id)
                msg = IGNORE_CMD.msg + mention.user_name + "."
            else:
                msg = ERR_MSG
        case '!intensity':
            # Set intensity and send notification, or send error if no value or not numeric
            try:
                STATE.intensity = max(1.0, min(100.0, float(command[1])))  # Normalizes between 1 and 100
                msg = INTENSITY_CMD.msg + str(STATE.intensity) + "."
            except (ValueError, IndexError):
                msg = ERR_MSG
        case '!interval':
            # Set interval and send notification, or send error if no value or not numeric
            try:
                STATE.interval = max(_MINIMUM_INTERVAL, int(command[1]))   #Normalizes to be above minimum
                msg = INTERVAL_CMD.msg + str(STATE.interval) + "."
            except (ValueError, IndexError):
                msg = ERR_MSG
        case '!keyword':
            # Set word and send notification, or send error if no value
            try:
                STATE.word = command[1]
                msg = KEYWORD_CMD.msg + STATE.word + "."
            except (IndexError):
                msg = ERR_MSG
        case '!length':
            # Set maximum length and send notification, or send error if no value or not numeric
            try:
                STATE.max_msg_length = max(_MINIMUM_MAX_LENGTH, int(command[1]))   #Normalizes to be above minimum
                msg = LENGTH_CMD.msg + str(STATE.max_msg_length) + "."
            except (ValueError, IndexError):
                msg = ERR_MSG
        case '!notarget':
            # Switch no_target mode and send notification
            STATE.no_target = not STATE.no_target
            msg = NOTARGET_CMD.msg + ("ON" if STATE.no_target else "OFF") + "."
        case '!timer':
            # Set timer and send notification, or send error if no value or not numeric
            try:
                STATE.cooldown = max(_MINIMUM_TIMEOUT, int(command[1]))     #Normalizes to be above minimum
                msg = TIMER_CMD.msg + str(STATE.cooldown) + "."
            except (ValueError, IndexError):
                msg = ERR_MSG
        case '!try':
            # Try to modify attached message and send result, or send error if no value
            if len(command) < 2:
                msg = ERR_MSG
            elif has_replaceable_elements(text := ' '.join(command[1:]), STATE.word):
                msg = replace_elements(text, STATE.word, STATE.intensity, STATE.adapt_word)
            else:
                msg = TRYOUT_CMD.msg
        case '!turnoff':
            # Send confirmation, then initiate shutdown
            await send_chat_message(TURNOFF_CMD.msg, 60)
            _initiate_shutdown("!turnoff command received")
            return
        case '!unignore':
            # Remove user from ignore and send notification, or send error if no @user
            if _has_mention_parameter(message):
                mention = message.fragments[2].mention
                STATE.ignore_ids.discard(mention.user_id)
                msg = UNIGNORE_CMD.msg + mention.user_name + "."
            else:
                msg = ERR_MSG
        case '!unvip':
            # Remove user from vip and send notification, or send error if no @user
            if _has_mention_parameter(message):
                mention = message.fragments[2].mention
                STATE.vip_ids.discard(mention.user_id)
                msg =  mention.user_name + UNVIP_CMD.msg
            else:
                msg = ERR_MSG
        case '!vip':
            # Add user to vip and send notification, or send error if no @user
            if _has_mention_parameter(message):
                mention = message.fragments[2].mention
                STATE.vip_ids.add(mention.user_id)
                msg = mention.user_name + VIP_CMD.msg
            else:
                msg = ERR_MSG
    await send_chat_message(msg, 60)


######## Chat message processing ########

def _is_valid_command_msg(event: ChatEvent) -> bool:
    """Checks that the event message is in form '@bot_mention !command opt_args' and that it was sent by a valid user"""
    sender = event.chatter_user_id
    fragments = event.message.fragments
    return (
        (
            sender == event.broadcaster_user_id                                         # Channel owner
            or sender in STATE.vip_ids                                                  # VIP users
            or (event.badges and any(b.set_id == 'moderator' for b in event.badges))    # Moderators
        )
        and fragments[0].type == 'mention'                                              # Starts with a mention
        and fragments[0].mention.user_id == BOT_ID                                      # Mention is the bot
        and len(fragments) > 1                                                          # Mention is followed by something
        and fragments[1].text.startswith(' !')                                          # Mention is followed by a command
    )

def _is_targetable_msg(event: ChatEvent) -> bool:
    """Checks if the event message can be targeted"""
    sender = event.chatter_user_id
    message = event.message
    return not (
        (STATE.no_target and sender==STATE.last_target)       # no_target mode is ON and user is the same as last target
        or message.text.startswith('!')				            # Begins with a !command
        or len(message.text) > STATE.max_msg_length			# Message is too long
        or any(f.type == 'mention' for f in message.fragments)	# Contains any @mention
        or sender in STATE.ignore_ids		                    # User cannot be a target
    )

async def _process_chat_msg(event: ChatEvent) -> None:
    if _is_valid_command_msg(event):
        # If the message starts with a valid command execute it
        logging.info(f"CMD <{event.chatter_user_name}> {event.message.text}")
        await _execute_command(event.message)
        return
    if (STATE.wait_messages > 0) or (time.time() - STATE.last_active <= STATE.cooldown):
        # If cooldown (either time or messages) is still on, log and decrease message cooldown
        STATE.wait_messages = max(0, STATE.wait_messages - 1) # minimum 0, to guard against bursts of messages during cooldown
        #_console_log_handler.terminator = ""
        logging.debug(".")
        #_console_log_handler.terminator = "\n"
        return
    logging.info(f"MSG <{event.chatter_user_name}> {event.message.text}")
    if not _is_targetable_msg(event):
        # If it's an untargetable message just log
        logging.info("Cannot modify")
        return
    if not has_replaceable_elements(event.message.text, STATE.word):
        # Preemptively check that the message has anything to modify, if not just log
        logging.info("Nothing to modify")
        return
    # Modify message, update state and send result
    msg = replace_elements(event.message.text, STATE.word, STATE.intensity, STATE.adapt_word)
    STATE.last_active = time.time()
    STATE.wait_messages = STATE.interval
    if STATE.no_target:
        STATE.last_target = event.chatter_user_id
    await send_chat_message(msg, 30)


######## WebSocket interactions ########

async def _keepalive_monitor(websocket):
    """Closes the websocket if no message has been received within the keepalive timeout, to trigger reconnection."""
    while True:
        await asyncio.sleep(STATE.keepalive_timeout)
        if time.time() - STATE.last_reception_time > STATE.keepalive_timeout:
            logging.warning("Keepalive timeout exceeded, forcing reconnection")
            await websocket.close()
            return

async def _handle_websocket_message(raw_data: str) -> None:
    STATE.last_reception_time = time.time()
    
    try:
        meta = MetadataOnly.model_validate_json(raw_data)
    except ValidationError as e:
        # If metadata is malformed the bot has to shutdown for safety
        # Malformed session_welcome or revocation would leave the bot deaf but unaware
        logging.critical(f"Could not parse message metadata, unsafe to continue, shutting down: {e}")
        _initiate_shutdown("unparseable WebSocket message")
        return

    msg_type = meta.metadata.message_type

    try:
        data = EventSubMessage.model_validate_json(raw_data)
    except ValidationError as e:
        match msg_type:
            case 'notification':
                logging.warning(f"Malformed notification, dropping it: {e}")
                return
            case 'session_reconnect':
                logging.warning(f"Malformed reconnection request, connection will forcefully reset in 30s: {e}")
                return
            case 'session_keepalive':
                # Just ignore it anyway
                return
            case _:
                logging.critical(f"Malformed {msg_type} message, unsafe to continue, shutting down: {e}")
                _initiate_shutdown(f"malformed {msg_type} message")
                return
    
    match msg_type:
        case 'notification':
            # If it's a notification handle it only if it's a chat message and not from the bot itself
            if (
                data.metadata.subscription_type == 'channel.chat.message'
                and data.payload.event.chatter_user_id != BOT_ID
            ):
                await _process_chat_msg(data.payload.event)
        case 'revocation':
            # If it's an EventSub subscription revocation for any reason initiate shutdown
            sub_type = data.payload.subscription.type
            reason = data.payload.subscription.status
            logging.critical(f"Subscription revoked for {sub_type}: {reason}")
            _initiate_shutdown(f"subscription revoked: {reason}")
        case 'session_reconnect':
            # If it's a reconnection request raise it to the connection loop
            new_url = data.payload.session.reconnect_url
            logging.info(f"Reconnection requested, new URL: {new_url}")
            raise _GracefulReconnect(new_url)
        case 'session_keepalive':
            # If it's a keepalive ping just log it
            logging.debug("Keepalive received")
        case 'session_welcome':
            # If it's the start of a connection subscribe to eventsub
            session = data.payload.session
            STATE.websocket_session_id = session.id
            if session.keepalive_timeout_seconds is not None:
                STATE.keepalive_timeout = session.keepalive_timeout_seconds + 10   # Adds 10s grace period (per Twitch documentation)
            logging.info(f"Session welcome with ID: {STATE.websocket_session_id}")
            await register_to_eventsub()
            if STATE.is_first_connection:
                await send_chat_message(STARTUP_MSG)
                STATE.is_first_connection = False

async def _websocket_connection_loop() -> None:
    """Starts the websocket client, then handles reconnections and closure"""
    url = _EVENTSUB_WEBSOCKET_URL
    backoff = _BASE_BACKOFF
    # This loop runs until a shutdown and attempts reconnection everytime the connection is closed or fails
    while not STATE.shutdown:
        try:
            async with websockets.connect(url) as websocket:
                logging.info(f'WebSocket connection opened to {url}')
                STATE.last_reception_time = time.time()
                backoff = _BASE_BACKOFF
                url = _EVENTSUB_WEBSOCKET_URL
                keepalive = asyncio.create_task(_keepalive_monitor(websocket))
                try:
                    async for message in websocket:
                        await _handle_websocket_message(message)
                        if STATE.shutdown:
                            # This ends the message loop on shutdown initiated by command or stop signal
                            # In the first case this happens immediately after the message itself that contained it so it's fine
                            # In the second it has to wait until any next message received, but that's bound by keepalive
                            # messages (10 s) and at worst has to delay for up to the maximum backoff of a sending
                            break
                finally:
                    # Cancel the current keepalive task (to reset it next iteration) regardless of what stopped the message loop
                    keepalive.cancel()
                if STATE.shutdown:
                    # This avoids the backoff logic at the end of the iteration in the same scenarios as above
                    continue
        except _GracefulReconnect as r:
            # On request for graceful reconnection, temporarily change url and let next iteration immediately reset connection
            url = r.temp_url
            continue
        except SubscriptionError as e:
            # If subscription to eventsub has completely failed the bot would run "deaf", so shut it down
            logging.critical(f"Subscription failed: {e}")
            _initiate_shutdown("subscription error")
            continue
        except AuthTokenError as e:
            # If there was a failure refreshing the auth token the bot would run "mute", so shut it down
            logging.critical(f"Failed to refresh auth token: {e}")
            _initiate_shutdown("token refreshing error")
            continue
        except websockets.exceptions.ConnectionClosed as e:
            # If the websocket connection was closed let next iteration reset it (after backoff)
            logging.error(f"WebSocket connection closed: {e}")
        except Exception as e:
            # On any other error just try to "start from scratch" next iteration (after backoff)
            logging.error(f"Unexpected error: {e}")
        #Exponential backoff, on consecutive connection fails wait with doubled delay until successful (or max)
        if backoff > _MAX_BACKOFF:
            logging.critical("Max reconnection backoff exceeded, shutting down")
            _initiate_shutdown("max reconnection backoff exceeded")
            continue
        logging.info(f"Reconnecting in {backoff}s")
        await asyncio.sleep(backoff)
        backoff = backoff * 2


######## Entry point ########

async def main():
    global _console_log_handler
    # Set up the logger
    log_level = logging.DEBUG if '--debug' in sys.argv else logging.INFO
    logging.Formatter.converter = time.gmtime
    _console_log_handler = logging.StreamHandler()
    _console_log_handler.setFormatter(logging.Formatter(
        fmt='%(asctime)s %(levelname)s %(message)s',
        datefmt='%a, %d %b %Y %H:%M:%S'
    ))
    logging.getLogger().addHandler(_console_log_handler)
    logging.getLogger().setLevel(log_level)
    _setup_signal_handlers()
    try:
        # Start connection loop
        async with aiohttp.ClientSession() as client:
            set_http_client(client)
            await _websocket_connection_loop()
    except Exception as e:
        # If any unexpected exception was raised log it
        logging.critical(f"Unhandled exception: {e}", exc_info=True)
    finally:
        # Save settings
        settings.REPLACEMENT_WORD = STATE.word
        settings.INTENSITY = STATE.intensity
        settings.WAIT_SECONDS = STATE.cooldown
        settings.WAIT_MESSAGES = STATE.interval
        settings.NOTARGET_MODE = STATE.no_target
        settings.VIP_IDS = list(STATE.vip_ids)
        settings.IGNORED_IDS = list(STATE.ignore_ids)
        settings.ADVANCED_MODE = not STATE.adapt_word
        settings.MAX_TARGET_LENGTH = STATE.max_msg_length
        try:
            save_settings()
        except SettingsSaveError as e:
            logging.error(f"Error while saving settings: {e}")
            logging.debug(f"Settings dump: {settings}")
