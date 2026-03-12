import os
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Dict

from bot.utils.checks import tortoise_bot_developer_only
from bot.utils.embed_handler import code_eval_embed, failure, success
from bot.constants import tortoise_guild_id

EXECUTE_URL = os.getenv("EXECUTION_API_URL")

LANG_ALIASES = {
    "py": "python",
    "python": "python",
    "js": "javascript",
    "javascript": "javascript",
    "java": "java",
}

view = discord.ui.View()
view.add_item(
    discord.ui.Button(
        label="Add to Server",
        emoji=discord.PartialEmoji(name="add", id=1481785944813342964),
        url="https://discord.com/oauth2/authorize?client_id=780132667265122315",
    )
)

class SandboxExec(commands.Cog):

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session = aiohttp.ClientSession()
        self.tracked: Dict[int, dict] = {}
        self.runtime_enabled = True

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
            if resp.status == 429:
                return {
                    "code": -1,
                    "output": "",
                    "std_log": "Rate limit exceeded. Please wait before executing again.",
                    "rate_limited": True,
                }
            if resp.status == 503:
                return {
                    "code": -1,
                    "output": "",
                    "std_log": "Engine is currently under maintenance. Please try again later.",
                    "maintenance": True,
                }

            if resp.status >= 500:
                return {
                    "code": -1,
                    "output": "",
                    "std_log": "Execution engine temporarily unavailable.",
                    "unavailable": True,
                }

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

        if result.get("rate_limited") or result.get("maintenance") or result.get("unavailable"):
            embed = failure(result.get("std_log"))
        else:
            embed = code_eval_embed(language, output, edited=edited, exit_code=exit_code, disable_extras=True)
            embed.set_footer(text=f"Powered by Hermes Engine", icon_url=f"https://lairesit.sirv.com/Tortoise/{language}.png")

        if target_message:
            await target_message.edit(embed=embed, view=view)
            return target_message
        else:
            return await channel.send(embed=embed, view=view)


    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.runtime_enabled or message.author.bot or not message.guild:
            return

        if message.guild.id != tortoise_guild_id:
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

        async with message.channel.typing():
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
        if not self.runtime_enabled or after.author.bot or not after.guild:
            return

        if after.guild.id != tortoise_guild_id:
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

        async with after.channel.typing():
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

    @app_commands.command(description="Disable runtime execution in this guild")
    @app_commands.check(tortoise_bot_developer_only)
    async def disable_runtime(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.runtime_enabled = False
        await interaction.followup.send(embed=success("Runtime Disabled"))

    @app_commands.command(description="Enable runtime execution in this guild")
    @app_commands.check(tortoise_bot_developer_only)
    async def enable_runtime(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.runtime_enabled = True
        await interaction.followup.send(embed=success("Runtime Enabled"))


async def setup(bot: commands.Bot):
    await bot.add_cog(SandboxExec(bot))
