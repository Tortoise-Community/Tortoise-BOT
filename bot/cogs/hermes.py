import os
import aiohttp
import discord
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Dict
from bot.utils.embed_handler import code_eval_embed

EXECUTE_URL = os.getenv("EXECUTION_API_URL")

LANG_ALIASES = {
    "py": "python",
    "python": "python",
    "js": "javascript",
    "javascript": "javascript",
    "java": "java",
}


class SandboxExec(commands.Cog):

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
            _, block = content.split("```", 1)
            block_content = block.split("```", 1)[0]

            first_line, *rest = block_content.split("\n")
            lang = first_line.strip().lower()
            code = "\n".join(rest)

            if not lang or not code.strip():
                return None

            return lang, code
        except Exception:
            return None


    async def _execute(self, language: str, code: str):
        payload = {
            "language": language,
            "code": code,
        }

        async with self.session.post(EXECUTE_URL, json=payload, timeout=30) as resp:
            return await resp.json()


    def _build_output(self, result: dict):
        exit_code = result.get("code")
        stdout = result.get("output", "") or ""
        stderr = result.get("std_log", "") or ""

        combined = stdout
        if exit_code != 0 and stderr:
            combined = combined + ("\n" if combined else "") + stderr

        if not combined:
            combined = "(no output)"

        if len(combined) > 1900:
            combined = combined[:1900] + "\n... (truncated)"

        return exit_code, combined

    async def _send_result(
        self,
        channel: discord.TextChannel,
        result: dict,
        language: str,
        edited: bool = False,
        target_message: discord.Message | None = None,
    ):
        exit_code, output = self._build_output(result)

        embed = code_eval_embed(language, output, edited=edited, exit_code=exit_code)
        embed.set_footer(text="powered by Hermes Engine")

        if target_message:
            await target_message.edit(embed=embed)
            return target_message
        else:
            return await channel.send(embed=embed)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        parsed = self._parse_block(message.content)
        if not parsed:
            return

        lang, code = parsed
        lang = LANG_ALIASES.get(lang)

        if not lang:
            await message.channel.send(
                "Unsupported language. Use python, javascript or java in the code block header."
            )
            return

        try:
            result = await self._execute(lang, code)
        except Exception:
            await message.channel.send("Execution request failed.")
            return

        bot_msg = await self._send_result(message.channel, result, lang)

        self.tracked[message.id] = {
            "created": datetime.utcnow(),
            "lang": lang,
            "bot_msg_id": bot_msg.id,
        }

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if after.author.bot or not after.guild:
            return

        meta = self.tracked.get(after.id)
        if not meta:
            return

        if datetime.utcnow() - meta["created"] > timedelta(minutes=2):
            self.tracked.pop(after.id, None)
            return

        parsed = self._parse_block(after.content)
        if not parsed:
            return

        lang, code = parsed
        lang = LANG_ALIASES.get(lang)

        if not lang:
            return

        try:
            result = await self._execute(lang, code)
        except Exception:
            return

        try:
            bot_msg = await after.channel.fetch_message(meta["bot_msg_id"])
        except Exception:
            return

        await self._send_result(
            after.channel,
            result,
            lang,
            edited=True,
            target_message=bot_msg,
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(SandboxExec(bot))
