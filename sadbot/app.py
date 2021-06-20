""" This module contains the main app class and friends """

import glob
import json
import re
import sqlite3
import time
from os.path import dirname, basename, isfile, join
from typing import Optional, Dict

import requests

from sadbot.message import Message
from sadbot.message_repository import MessageRepository
from sadbot.config import MAX_REPLY_LENGTH, UPDATES_TIMEOUT
from sadbot.bot_reply import (
    BotReply,
    BOT_REPLY_TYPE_TEXT,
    BOT_REPLY_TYPE_IMAGE,
    BOT_REPLY_TYPE_AUDIO,
    BOT_REPLY_TYPE_FILE,
    BOT_REPLY_TYPE_VOICE,
)


def snake_to_pascal_case(snake_str: str):
    """Converts a given snake_case string to PascalCase"""
    components = snake_str.split("_")
    return "".join(x.title() for x in components[0:])


class App:
    """Main app class, starts the bot when it's called"""

    def __init__(self, token: str) -> None:
        self.base_url = f"https://api.telegram.org/bot{token}/"
        self.classes = {}
        con = sqlite3.connect("./messages.db")
        self.classes.update({"Connection": con})
        self.message_repository = MessageRepository(con)
        self.classes.update({"MessageRepository": self.message_repository})
        self.commands = []
        self.load_commands()
        self.start_bot()

    def load_commands(self):
        """Loads the bot commands"""
        commands = glob.glob(join(dirname(__file__), "commands", "*.py"))
        for command_name in [basename(f)[:-3] for f in commands if isfile(f)]:
            if command_name == "__init__":
                continue
            class_name = snake_to_pascal_case(command_name) + "BotCommand"
            arguments = []
            command_class = getattr(
                __import__("sadbot.commands." + command_name, fromlist=[class_name]),
                class_name,
            )
            if command_class.__init__.__class__.__name__ == "function":
                arguments_list = command_class.__init__.__annotations__
                for argument_name in arguments_list:
                    arguments.append(
                        self.classes[arguments_list[argument_name].__name__]
                    )
            command_class = command_class(*arguments)
            self.commands.append(
                {"regex": command_class.command_regex, "class": command_class}
            )

    def get_updates(self, offset: Optional[int] = None) -> Optional[Dict]:
        """Retrieves updates from the telelegram API"""
        url = f"{self.base_url}getUpdates?timeout={UPDATES_TIMEOUT}"
        if offset:
            url = f"{url}&offset={offset + 1}"
        req = requests.get(url)
        if not req.ok:
            print(f"Failed to retrieve updates from server - details: {req.json()}")
            return None

        return json.loads(req.content)

    def send_message(self, chat_id: int, reply: BotReply) -> Optional[Dict]:
        """Sends a message"""
        data = {"chat_id": chat_id}
        files = None
        if reply.reply_type == BOT_REPLY_TYPE_TEXT:
            api_method = "sendMessage"
            if not reply.reply_text:
                return None
            reply_text = reply.reply_text
            if len(reply_text) > MAX_REPLY_LENGTH:
                reply_text = reply_text[:MAX_REPLY_LENGTH] + "..."
            data.update({"text": reply_text})
            parsemode = reply.reply_text_parsemode
            if parsemode is not None:
                data.update({"parsemode": parsemode})
        elif reply.reply_type == BOT_REPLY_TYPE_IMAGE:
            api_method = "sendPhoto"
            files = {"photo": reply.reply_image}
        elif reply.reply_type == BOT_REPLY_TYPE_AUDIO:
            api_method = "sendAudio"
            files = {"audio": reply.reply_audio}
        elif reply.reply_type == BOT_REPLY_TYPE_FILE:
            api_method = "sendDocument"
            files = {"file": reply.reply_file}
        elif reply.reply_type == BOT_REPLY_TYPE_VOICE:
            api_method = "sendVoice"
            files = {"voice": reply.reply_voice}
        req = requests.post(
            f"{self.base_url}{api_method}",
            data=data,
            headers={"Conent-Type": "application/json"},
            files=files,
        )
        if not req.ok:
            print(f"Failed sending message - details: {req.json()}")
            return None
        return json.loads(req.content)

    def get_replies(self, message: Message) -> Optional[dict]:
        """Checks if a bot command is triggered and gets its reply"""
        text = message.text
        if not text:
            return None
        messages = []
        for command in self.commands:
            try:
                if re.fullmatch(re.compile(command["regex"]), text):
                    reply_message = command["class"].get_reply(message)
                    if reply_message is None:
                        continue
                    messages.append(reply_message)
            except re.error:
                return None
        return messages

    def start_bot(self) -> None:
        """Starts the bot"""
        update_id = None
        while True:
            updates = self.get_updates(offset=update_id) or {}
            for item in updates.get("result", []):
                update_id = item["update_id"]
                try:
                    text = str(item["message"]["text"])
                except (ValueError, KeyError, TypeError):
                    continue

                if not text:
                    continue

                message = item["message"]
                message = Message(
                    message["message_id"],
                    message["from"]["first_name"],
                    message["from"]["id"],
                    message["chat"]["id"],
                    text,
                    message.get("reply_to_message", {}).get("message_id"),
                )
                replies_info = self.get_replies(message)
                self.message_repository.insert_message(message)
                if replies_info is None:
                    continue
                for reply_info in replies_info:
                    sent_message = self.send_message(message.chat_id, reply_info) or {}
                    # this needs to be done better
                    if (
                        sent_message.get("result")
                        and reply_info.reply_type == BOT_REPLY_TYPE_TEXT
                    ):
                        result = sent_message.get("result")
                        message = Message(
                            result["message_id"],
                            result["from"]["first_name"],
                            result["from"]["id"],
                            message.chat_id,
                            reply_info.reply_text,
                            None,
                        )
                        self.message_repository.insert_message(message)
            time.sleep(1)
