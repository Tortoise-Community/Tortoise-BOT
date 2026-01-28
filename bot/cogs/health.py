from __future__ import annotations

import os
import time
import platform
from datetime import datetime, timedelta
from typing import Dict, List

import psutil
import discord
from discord.ext import commands
from aiohttp import web
from discord import app_commands
from bot.constants import rate_limit_minutes

class HealthCheck(commands.Cog):
    """
    Exposes health endpoints for monitoring the bot.
    """

    def __init__(
        self,
        bot: commands.Bot,
        host: str = "0.0.0.0",
        port: int = 8080,
    ):
        self.bot = bot
        self.host = host
        self.port = port

        self.start_time = time.time()

        self.rate_limit_window = timedelta(minutes=rate_limit_minutes)
        self.max_requests = 2
        self.client_requests: Dict[str, List[datetime]] = {}

        self.app = web.Application()
        self.app.add_routes(
            [
                web.get("/health", self.health),
                web.head("/ready", self.ready),
            ]
        )

        self.runner: web.AppRunner | None = None
        self.site: web.TCPSite | None = None

        self.bot.loop.create_task(self._start_server())


    def _is_rate_limited(self, request: web.Request) -> bool:
        # Support reverse proxies
        client_ip = (
            request.headers.get("X-Forwarded-For", request.remote)
            or "unknown"
        )
        # If multiple IPs are present, take the first
        client_ip = client_ip.split(",")[0].strip()

        now = datetime.utcnow()
        window_start = now - self.rate_limit_window

        timestamps = self.client_requests.get(client_ip, [])

        timestamps = [t for t in timestamps if t > window_start]

        if len(timestamps) >= self.max_requests:
            self.client_requests[client_ip] = timestamps
            return True

        timestamps.append(now)
        self.client_requests[client_ip] = timestamps
        return False


    async def health(self, request: web.Request) -> web.Response:
        if self._is_rate_limited(request):
            return web.json_response(
                {
                    "status": "rate_limited",
                    "retry_after_minutes": rate_limit_minutes,
                },
                status=429,
            )

        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / 1024 / 1024

        data = {
            "status": "ok",
            "build_version": self.bot.build_version,
            "uptime_seconds": int(time.time() - self.start_time),
            "latency_ms": round(self.bot.latency * 1000, 2),
            "guilds": len(self.bot.guilds),
            "users": sum(g.member_count or 0 for g in self.bot.guilds),
            "python_version": platform.python_version(),
            "discord_py_version": discord.__version__,
            "memory_mb": round(mem_mb, 2),
            "pid": os.getpid(),
        }

        return web.json_response(data)

    async def ready(self, request: web.Request) -> web.Response:
        if self._is_rate_limited(request):
            return web.Response(text="RATE LIMITED", status=429)

        if self.bot.is_ready():
            return web.Response(text="READY", status=200)

        return web.Response(text="NOT READY", status=503)


    async def _start_server(self):
        await self.bot.wait_until_ready()

        self.runner = web.AppRunner(self.app)
        await self.runner.setup()

        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()

        print(f"🫀Health checks available at http://{self.host}:{self.port}")

    async def cog_unload(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

    @app_commands.checks.cooldown(1, 60)
    @app_commands.command(
        name="health",
        description="Show bot health, status, and system statistics"
    )
    async def health_command(self, interaction: discord.Interaction):
        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / 1024 / 1024
        uptime = int(time.time() - self.start_time)

        embed = discord.Embed(
            title="🫀 Snappy Bot Health Status",
            color=discord.Color.green(),
            timestamp=datetime.utcnow()
        )

        embed.add_field(name="Status", value="🟢 Healthy", inline=True)
        embed.add_field(name="Build", value=f"`{self.bot.build_version}`", inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000, 2)} ms", inline=True)

        embed.add_field(name="Uptime", value=f"{uptime} seconds", inline=True)
        embed.add_field(name="Guilds", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(
            name="Users",
            value=str(sum(g.member_count or 0 for g in self.bot.guilds)),
            inline=True,
        )

        embed.add_field(name="Memory", value=f"{round(mem_mb, 2)} MB", inline=True)
        embed.add_field(name="Python", value=platform.python_version(), inline=True)
        embed.add_field(name="discord.py", value=discord.__version__, inline=True)

        embed.add_field(
            name="Website",
            value="[snappy-bot.tortoisecommunity.org](https://snappy-bot.tortoisecommunity.org)",
            inline=False,
        )

        embed.set_footer(text="Snappy Bot • Health Monitor")

        await interaction.response.send_message(embed=embed, ephemeral=False)

    @health_command.error
    async def health_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Try again in {int(error.retry_after)} seconds.",
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    host = os.getenv("HEALTH_HOST", "0.0.0.0")
    port = os.getenv("HEALTH_PORT", "8080")

    await bot.add_cog(HealthCheck(bot, host=host, port=port))