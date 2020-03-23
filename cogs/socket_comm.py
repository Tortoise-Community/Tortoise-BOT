import os
import json
import socket
import logging
from typing import List, Dict
from discord.ext import commands
from discord import HTTPException, Member
from discord.activity import ActivityType
import aiohttp

logger = logging.getLogger(__name__)

tortoise_guild_id = 577192344529404154
tortoise_log_channel_id = 581139962611892229
verified_role_id = 599647985198039050
unverified_role_id = 605808609195982864


class SocketCommunication(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auth_token = os.getenv("SOCKET_AUTH_TOKEN")
        self.verified_clients = set()
        self._socket_server = SocketCommunication.create_server()
        self.task = self.bot.loop.create_task(self.run_server(self._socket_server))

    def cog_unload(self):
        logger.info("Unloading socket comm, closing connections.")
        logger.info(f"Canceling server task..")
        self.task.cancel()

        for client in self.verified_clients:
            try:
                logger.info(f"Closing client {client}")
                client.close()
            except OSError:
                pass

        try:
            logger.info("Server shutdown..")
            self._socket_server.shutdown(socket.SHUT_RDWR)
            logger.info("Server closing..")
            self._socket_server.close()
        except OSError:
            # Not supported on Windows
            pass

    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.guild.id != tortoise_guild_id:
            return

        logger.info(f"Checking new member {member.name}")
        async with aiohttp.ClientSession() as session:
            data = await session.get(f"https://api.tortoisecommunity.ml/verify-confirmation/{member.id}")
            data = await data.json(content_type=None)

        verified = data.get("verified")
        if verified is None:
            # User doesn't exist in database, add him
            data = {"user_id": member.id, "guild_id": member.guild.id}
            logger.info(f"Updating database {data}")
            async with aiohttp.ClientSession() as session:
                await session.post("https://api.tortoisecommunity.ml/members", json=data)
            logger.info("Database update done.")
        elif verified:
            logger.info(f"Member {member.id} is verified in database, adding roles..")
            await self.add_verified_roles_to_member(member)
        else:
            logger.info(f"Member {member.id} is not verified in database. Waiting for socket")

    @staticmethod
    def create_server():
        logger.info("Starting socket comm server...")
        server = socket.socket()
        server.bind(("0.0.0.0", 15555))
        server.listen(3)
        server.setblocking(False)
        logger.info("Socket comm server started.")
        return server

    async def run_server(self, server: socket.socket):
        while True:
            client, _ = await self.bot.loop.sock_accept(server)
            client_name = client.getpeername()
            logger.info(f"{client_name} connected.")
            self.bot.loop.create_task(self.handle_client(client, client_name))

    async def handle_client(self, client, client_name: str):
        request = None
        while request != "quit":
            try:
                request = (await self.bot.loop.sock_recv(client, 255)).decode("utf8")
            except ConnectionResetError:
                # If the client disconnects without sending quit.
                logger.info(f"{client_name} disconnected.")
                break

            if not request:
                logger.info("Empty, closing.")
                break

            try:
                request = json.loads(request)
            except json.JSONDecodeError:
                response = {"status": 400, "response": "Not a valid JSON formatted request."}
                await self.send_to_client(client, json.dumps(response))
                logger.info(f"{client_name}:{response}\n{request}")
                continue

            logger.info(f"Server got:\n{request}")

            if client not in self.verified_clients:
                token = request.get("Auth")
                if token is not None and token == self.auth_token:
                    self.verified_clients.add(client)
                    response = {"status": 200}
                    await self.send_to_client(client, json.dumps(response))
                    logger.info(f"{client_name} successfully authorized.")
                    continue
                else:
                    response = {"status": 401, "response": "Verification unsuccessful, closing conn."}
                    await self.send_to_client(client, json.dumps(response))
                    logger.info(f"{client_name}:{response}\n{request}")
                    break

            await self.parse_request(request, client)
        logger.info(f"Closing {client_name}")
        client.close()

    async def send_to_client(self, client, msg):
        try:
            await self.bot.loop.sock_sendall(client, bytes(msg.encode("unicode_escape")))
        except BrokenPipeError:
            # If the client closes the connection too quickly or just does't even bother listening to response we'll
            # get this, so just ignore
            pass

    async def parse_request(self, request: dict, client):
        """
        Dict with possible keys:
        "Send" sends value to text channel
        """
        client_name = client.getpeername()
        response = {"status": 200}

        send = request.get("Send")
        if send is not None:
            logger.info(f"Beginning SEND request from {client_name}")
            await self.send_to_channel_test(f"Client says:{send}")
            await self.send_to_client(client, json.dumps(response))
            logger.info(f"Done SEND request from {client_name}")

        members = request.get("Members")
        if members is not None:
            logger.info(f"Beginning MEMBERS request from {client_name}")
            response["Members"] = await self.get_member_activities(members)
            logger.info(f"Done MEMBERS request from {client_name}, returning {response}")
            await self.send_to_client(client, json.dumps(response))
            logger.info(f"{client_name} returned members successfully.")

        verify = request.get("Verify")
        if verify is not None:
            logger.info(f"Got verify: {verify}")
            response = await self.verify_member(verify)
            logger.info(f"Done MEMBERS request from {client_name}, returning {response}")
            await self.send_to_client(client, json.dumps(response))

    async def send_to_channel_test(self, message):
        logger.info(f"Sending {message} to channel.")
        test_channel = self.bot.get_channel(581139962611892229)
        await test_channel.send(message)
        logger.info(f"Sent {message} to channel!")

    async def get_member_activities(self, members: List[int]) -> Dict[int, str]:
        response_activities = {}
        tortoise_guild = self.bot.get_guild(577192344529404154)
        logger.info(f"Processing members: {members}")
        for member_id in members:
            logger.info(f"Processing member: {member_id}")
            member = tortoise_guild.get_member(int(member_id))

            if member is None:
                logger.info(f"Member {member_id} not found.")
                response_activities[member_id] = "None"
                continue

            activity = member.activity
            if activity is None:
                logger.info(f"Member {member_id} does not have any activity.")
                response_activities[member_id] = "None"
                continue
            elif activity.type == ActivityType.playing:
                logger.info(f"Member {member_id} is playing.")
                response_activities[member_id] = f"Playing {activity.name}"
            elif activity.type == ActivityType.streaming:
                logger.info(f"Member {member_id} is streaming.")
                response_activities[member_id] = f"Streaming {activity}"
            else:
                # For cases where it is None, CustomActivity or Activity(watching, listening)
                logger.info(activity.type)
                logger.info(type(activity.type))
                response_activities[member_id] = str(activity)

        logger.info(f"Processing members done, returning: {response_activities}")
        return response_activities

    async def verify_member(self, member_id: str) -> Dict[int, str]:
        try:
            member_id = int(member_id)
        except ValueError:
            return {400: "ID formatted wrong."}

        guild = self.bot.get_guild(tortoise_guild_id)
        verified_role = guild.get_role(verified_role_id)
        unverified_role = guild.get_role(unverified_role_id)
        log_channel = guild.get_channel(tortoise_log_channel_id)
        if verified_role is None or guild is None or log_channel is None or unverified_role is None:
            return {500: "Tortoise IDs not found."}

        member = guild.get_member(member_id)
        if member is None:
            return {404: "Member not found"}

        try:
            await member.remove_roles(unverified_role)
        except HTTPException:
            return {500: "Bot could't remove unverified role"}

        data = {"user_id": member.id, "guild_id": guild.id, "name": str(member), "verified": True}
        logger.info(f"Updating database {data}")
        async with aiohttp.ClientSession() as session:
            await session.put(f"https://api.tortoisecommunity.ml/members/edit/{member.id}", json=data)
        logger.info("Database update done.")

        await member.add_roles(verified_role)
        await member.send("You are now verified.")
        await log_channel.send(f"{member.mention} is now verified.")
        return {200: "Successfully verified."}

    async def add_verified_roles_to_member(self, member: Member):
        guild = self.bot.get_guild(tortoise_guild_id)
        verified_role = guild.get_role(verified_role_id)
        unverified_role = guild.get_role(unverified_role_id)
        log_channel = guild.get_channel(tortoise_log_channel_id)
        try:
            await member.remove_roles(unverified_role)
        except HTTPException:
            logger.info(f"Bot could't remove unverified role {unverified_role}")

        await member.add_roles(verified_role)
        await member.send("Welcome back.")
        await log_channel.send(f"{member.mention} has returned.")


def setup(bot):
    bot.add_cog(SocketCommunication(bot))
