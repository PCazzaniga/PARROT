"""
Module with all the messages related to the bot commands.
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class Command_msgs:
    help_msg: str
    msg: str

DEFAULT_MSG = "Unrecognized command, use '!commands' to see the list."

ERR_MSG = "Invalid command syntax or value, use '!help !<command>' for more info."

STARTUP_MSG = (
    "Hello, World ! :) I'm here to randomly repeat chat messages, with a twist "
    "(I have many commands for customization, which mods can use by @\u200Bing me)."
)

COMMANDS_LIST = Command_msgs(
    help_msg="Seriously ?",
    msg=(
        "!advanced, !ignore, !intensity, !interval, !keyword, !length, "
        "!notarget, !timer, !try, !turnoff, !unignore, !unvip, !vip "
        "(Use '!help !<command>' for more info on each)."
    )
)

ADVANCED_CMD = Command_msgs(
    help_msg="'!advanced' switches whether or not complex logic will be used to modify chat messages when they don't match the keyword's plurality.",
    msg="Advanced mode is "
)

IGNORE_CMD = Command_msgs(
    help_msg="'!ignore @\u200B<user>' makes the user's chat messages unmodifiable (recommended for other bots).",
    msg="I will not modify chat messages from "
)

INTENSITY_CMD = Command_msgs(
    help_msg="'!intensity <number>' sets the likelihood of modifying eligible words in chat messages (1 to 100).",
    msg="Intensity set to "
)

INTERVAL_CMD = Command_msgs(
    help_msg="'!interval <number>' sets the chat messages to wait between activations (recommended in quiet chatrooms, minimum 5).",
    msg="Interval of chat messages between activations set to "
)

KEYWORD_CMD = Command_msgs(
    help_msg="'!keyword <word>' sets the keyword used to modify chat messages. Currently: ",
    msg="Keyword set to "
)

LENGTH_CMD = Command_msgs(
    help_msg="'!length <number>' sets the maximum characters length for a message to be modifiable (minimum 30).",
    msg="I cannot modify chat messages with characters count above "
)

NOTARGET_CMD = Command_msgs(
    help_msg="'!notarget' switches whether or not users can be targeted multiple times in a row.",
    msg="No-Target mode is "
)

TIMER_CMD = Command_msgs(
    help_msg="'!timer <seconds>' sets the cooldown between activations (recommended in busy chatrooms, minimum 30)",
    msg="Cooldown timer set to "
)

TRYOUT_CMD = Command_msgs(
    help_msg="'!try <text>' attempts to modify the provided text.",
    msg="Nothing to modify."
)

TURNOFF_CMD = Command_msgs(
    help_msg="'!turnoff' completely shuts down the bot",
    msg="Farewell, cruel world :("
)

UNIGNORE_CMD = Command_msgs(
    help_msg="'!unignore @\u200B<user>' makes the user's chat messages modifiable again.",
    msg="I can again modify chat messages from "
)

UNVIP_CMD = Command_msgs(
    help_msg="'!unvip @\u200B<user>' disables the user from using my commands (unless they're a mod)",
    msg = " can no longer use my commands."
)

VIP_CMD = Command_msgs(
    help_msg="'!vip @\u200B<user>' enables the user to use my commands like mods",
    msg = " can now use my commands."
)

