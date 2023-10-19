"""Spoiler bot command"""

from typing import Optional, List
from sadbot.app import App

from sadbot.command_interface import CommandInterface, BOT_HANDLER_TYPE_MESSAGE
from sadbot.message import (
    Message,
    MESSAGE_FILE_TYPE_PHOTO,
    MESSAGE_FILE_TYPE_VIDEO,
)
from sadbot.message_repository import MessageRepository
from sadbot.bot_action import (
    BotAction,
    BOT_ACTION_TYPE_DELETE_MESSAGE,
    BOT_ACTION_TYPE_REPLY_VIDEO,
    BOT_ACTION_TYPE_REPLY_TEXT,
    BOT_ACTION_TYPE_REPLY_IMAGE,
)


class SpoilerBotCommand(CommandInterface):
    """This is the spoiler bot command class"""

    def __init__(self, app: App, message_repository: MessageRepository):
        """Initializes the spoiler command"""
        self.app = app
        self.message_repository = message_repository

    @property
    def handler_type(self) -> int:
        """Returns the type of event handled by the command"""
        return BOT_HANDLER_TYPE_MESSAGE

    @property
    def command_regex(self) -> str:
        """Returns the regex for matching spoiler commands"""
        return r"(\.|!|/)([sS])(.*)"

    def get_reply(self, message: Optional[Message] = None) -> Optional[List[BotAction]]:
        """Spoiler"""
        if message is None or message.reply_id is None or message.text is None:
            return None
        reply_message = self.message_repository.get_reply_message(message)
        if reply_message is None:
            return None
        file_bytes = self.app.get_file_from_id(reply_message.file_id)
        action = None
        sender = reply_message.sender_name
        if reply_message.sender_username:
            sender = f"@{reply_message.sender_username}"
        reply_text = f"Sender: {sender}"
        if reply_message.text:
            reply_text += f'\n<span class="tg-spoiler">{reply_message.text}</span>'
        if reply_message.file_type == MESSAGE_FILE_TYPE_PHOTO:
            action = BotAction(
                BOT_ACTION_TYPE_REPLY_IMAGE,
                reply_image=file_bytes,
                reply_spoiler=True,
                reply_text=reply_text,
                reply_text_parse_mode="HTML",
            )
        elif reply_message.file_type == MESSAGE_FILE_TYPE_VIDEO:
            action = BotAction(
                BOT_ACTION_TYPE_REPLY_VIDEO,
                reply_video=file_bytes,
                reply_spoiler=True,
                reply_text=reply_text,
                reply_text_parse_mode="HTML",
            )
        else:
            action = BotAction(
                BOT_ACTION_TYPE_REPLY_TEXT,
                reply_text=reply_text,
                reply_text_parse_mode="HTML",
            )
        return [
            BotAction(
                BOT_ACTION_TYPE_DELETE_MESSAGE,
                reply_delete_message_id=message.reply_id,
            ),
            action,
        ]
