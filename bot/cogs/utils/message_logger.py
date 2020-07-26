from datetime import datetime

from discord import Message, Embed


class MessageLogger:
    def __init__(self, mod_id: int, user_id: int):
        self.filename = f"{mod_id}--{user_id}.txt"
        self._log = [f"{datetime.now()} mod {mod_id} user {user_id} mod mail started."]

    def __str__(self):
        return "\n".join(self._log)

    def add_message(self, message: Message):
        new_log = f"{datetime.now()} {self.format_message_to_string(message)}"
        self._log.append(new_log)

    @classmethod
    def format_message_to_string(cls, message: Message) -> str:
        temp_msg = [
            f"author:{message.author}",
            f"content:{message.content}"
        ]

        for attachment in message.attachments:
            temp_msg.append(f"attachment:{attachment.filename} url:{attachment.url}")

        return "\t".join(temp_msg)

    def add_embed(self, embed: Embed):
        """
        We are not expecting embeds from mod/user but bot can send embed in case of info message (mod-mail closed etc)
        """
        self._log.append(f"{datetime.now()} embed:{embed.description}")
