"""Reddit bot command"""
import html
import json
from typing import Optional, List

import os
import random
import requests
import validators
from yt_dlp.YoutubeDL import YoutubeDL

from sadbot.command_interface import CommandInterface, BOT_HANDLER_TYPE_MESSAGE
from sadbot.message import Message

from sadbot.bot_action import (
    BOT_ACTION_TYPE_NONE,
    BOT_ACTION_TYPE_REPLY_IMAGE,
    BOT_ACTION_TYPE_REPLY_VIDEO,
    BotAction,
    BOT_ACTION_TYPE_REPLY_TEXT,
)


def handle_post(post) -> Optional[List[BotAction]]:
    """Return a bot action from the json of a reddit post"""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:98.0) Gecko/20100101 Firefox/98.0"
    }
    score = post["score"]
    title = post["title"]
    num_comments = post["num_comments"]
    permalink = post["permalink"]
    action = BotAction(BOT_ACTION_TYPE_NONE)
    if post["selftext"] != "":
        text = html.unescape(post["selftext"])
        caption = (
            f"{title}\n{text}\nScore: {score}\n"
            + f"[Number of comments: {num_comments}](reddit.com{permalink})"
        )
        action = BotAction(
            BOT_ACTION_TYPE_REPLY_TEXT,
            reply_text=caption,
            reply_text_parse_mode="Markdown",
        )
    elif post["domain"] == "v.redd.it":
        caption = f"{title}\nLink: reddit.com{permalink}"
        file_name = str(random.randint(10000000000, 35000000000)) + ".mp4"
        ydl_opts = {
            "final_ext": "mp4",
            "outtmpl": file_name,
        }
        with YoutubeDL(ydl_opts) as ydl:
            try:
                ydl.download(post["url"])
            # pylint: disable=bare-except
            except:
                return [
                    BotAction(
                        BOT_HANDLER_TYPE_MESSAGE,
                        reply_text="Something went wrong.",
                    )
                ]

        with open(file_name, "rb") as file:
            buf = file.read()
        os.remove(file_name)
        action = BotAction(
            BOT_ACTION_TYPE_REPLY_VIDEO,
            reply_video=buf,
            reply_text=caption,
        )
    elif post["domain"] == "i.redd.it":
        caption = (
            f"*{title}*\nScore: {score}\n"
            + f"[Number of comments: {num_comments}](reddit.com{permalink})"
        )
        img = requests.get(post["url"], headers=headers)
        action = BotAction(
            BOT_ACTION_TYPE_REPLY_IMAGE,
            reply_image=img.content,
            reply_text=caption,
            reply_text_parse_mode="Markdown",
        )
    elif post["thumbnail"] != "":
        caption = (
            f"*{title}*\nScore: {score}\n"
            + f"[Number of comments: {num_comments}](reddit.com{permalink})"
        )
        if not validators.url(post["thumbnail"]):
            return None
        img = requests.get(post["thumbnail"], headers=headers)
        action = BotAction(
            BOT_ACTION_TYPE_REPLY_IMAGE,
            reply_image=img.content,
            reply_text=caption,
            reply_text_parse_mode="Markdown",
        )
    else:
        caption = (
            f'*{title}*\nScore: {post["url"]}\n'
            + f"[Number of comments: {num_comments}](reddit.com{permalink})"
        )
        action = BotAction(
            BOT_ACTION_TYPE_REPLY_TEXT,
            reply_text=caption,
            reply_text_parse_mode="Markdown",
        )
    return [action]


class RedditBotCommand(CommandInterface):
    """This is the sample command bot command class"""

    @property
    def handler_type(self) -> int:
        """Here is the type of event handled by the command"""
        return BOT_HANDLER_TYPE_MESSAGE

    @property
    def command_regex(self) -> str:
        """Here is the regex that triggers this bot command"""
        return r"([.]|[!])[Rr][Ee][Dd]{2}[Ii][Tt].*"

    def get_reply(self, message: Optional[Message] = None) -> Optional[List[BotAction]]:
        return [BotAction(BOT_ACTION_TYPE_REPLY_TEXT, reply_text="You are the most pathetic excuse of a human being I have ever seen. I hate you with the strength of a 1000 stars, and I genuinely hope that you die the most painful and slow death imaginable. Your very existence disgusts me and everybody who had the misfortune of ever resting their eyes on God's greatest mistake (I'm talking about you, in case I didn't get through your thick skull), and all of us want you to end your meaningless, parasitic existence, and for your hideous corpse to be sent far away. The only purpose your pitiful life has is to feed off the money, time, and resources of the people around you, without contributing a single joy or doing something useful. I almost feel sorry for you, as the very idea of that kind of painful, disabled cum stain of an existence brings a tear to my eye. If only you weren't a constant annoyance to everyone around you, narcissistic and the least likeable person in your city. You have the usefulness of someone with Down syndrome, and the likeablity of a child rapist. So, with that in mind, you should stick the nearest fork into the nearest outlet. Maybe someone will give a shit about you for a week and forget about you a month later.")]
