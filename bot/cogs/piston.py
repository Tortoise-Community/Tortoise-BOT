import aiohttp
import discord
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Dict
from bot.utils.embed_handler import code_eval_embed

PISTON_URL = "https://emkc.org/api/v2/piston/execute"

LANG_ALIASES = {
    "py": "python",
    "python": "python",
    "js": "javascript",
    "javascript": "javascript",
    "ts": "typescript",
    "c": "c",
    "cpp": "cpp",
    "c++": "cpp",
    "java": "java",
    "rs": "rust",
    "rust": "rust",
    "go": "go",
}


class Piston(commands.Cog):
    """Piston-style code execution cog with edit listening."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()

        self.tracked: Dict[int, dict] = {}

    def cog_unload(self):
        self.bot.loop.create_task(self.session.close())

    def _parse_block(self, content: str):
        if not content.startswith("/run"):
            return None

        if "```" not in content:
            return None

        try:
            header, block = content.split("```", 1)
            block_content = block.split("```", 1)[0]

            first_line, *rest = block_content.split("\n")
            lang = first_line.strip().lower()
            code = "\n".join(rest)

            return lang, code
        except Exception:
            return None

    async def _execute(self, language: str, code: str):
        payload = {
            "language": language,
            "version": "*",
            "files": [{"name": "main", "content": code}],
            "stdin": ""
        }

        async with self.session.post(PISTON_URL, json=payload, timeout=30) as resp:
            return await resp.json()


    async def _send_result(self, channel: discord.TextChannel, result: dict, language: str):
        if "run" not in result:
            return await channel.send("Execution failed: invalid response")

        run = result["run"]
        stdout = run.get("stdout", "")
        stderr = run.get("stderr", "")
        output = stdout + ("\n" + stderr if stderr else "")

        embed = code_eval_embed(language, output)
        return await channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        parsed = self._parse_block(message.content)
        if not parsed:
            return

        lang, code = parsed
        lang = LANG_ALIASES.get(lang, lang)

        result = await self._execute(lang, code)
        bot_msg = await self._send_result(message.channel, result, lang)

        # track message for edits
        self.tracked[message.id] = {
            "created": datetime.utcnow(),
            "lang": lang,
            "bot_msg_id": bot_msg.id
        }

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author.bot:
            return

        meta = self.tracked.get(after.id)
        if not meta:
            return

        # 2 minute edit window
        if datetime.utcnow() - meta["created"] > timedelta(minutes=2):
            self.tracked.pop(after.id, None)
            return

        parsed = self._parse_block(after.content)
        if not parsed:
            return

        lang, code = parsed
        lang = LANG_ALIASES.get(lang, lang)

        try:
            result = await self._execute(lang, code)
        except Exception:
            return

        channel = after.channel
        try:
            bot_msg = await channel.fetch_message(meta["bot_msg_id"])
        except Exception:
            return

        # update embed
        if "run" not in result:
            return

        run = result["run"]
        stdout = run.get("stdout", "")
        stderr = run.get("stderr", "")
        output = stdout + ("\n" + stderr if stderr else "")

        if not output:
            output = "(no output)"

        if len(output) > 1900:
            output = output[:1900] + "\n... (truncated)"

        embed = code_eval_embed(lang, output, edited=True)
        await bot_msg.edit(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Piston(bot))
