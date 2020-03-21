import os
import json
import socket
import logging
from sys import stdout
from typing import List, Dict
from discord.ext import commands
from discord.activity import ActivityType

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(message)s")
console = logging.StreamHandler(stdout)
console.setFormatter(formatter)
logger.addHandler(console)


class SocketCommunication(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.auth_token = os.getenv("SOCKET_AUTH_TOKEN")
        self.verified_clients = set()
        logger.debug("Starting socket comm...")
        self._socket_server = SocketCommunication.create_server()
        self.task = self.bot.loop.create_task(self.run_server(self._socket_server))

    def cog_unload(self):
        logger.debug("Unloading socket comm, closing connections.")
        logger.debug(f"Canceling server task..")
        self.task.cancel()

        for client in self.verified_clients:
            try:
                logger.debug(f"Closing client {client}")
                client.close()
            except OSError:
                pass

        try:
            logger.debug("Server shutdown..")
            self._socket_server.shutdown(socket.SHUT_RDWR)
            logger.debug("Server closing..")
            self._socket_server.close()
        except OSError:
            # Not supported on Windows
            pass

    @staticmethod
    def create_server():
        server = socket.socket()
        server.bind(("0.0.0.0", 15555))
        server.listen(3)
        server.setblocking(False)
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
                logger.debug(f"{client_name} disconnected.")
                break

            if not request:
                logger.debug("Empty, closing.")
                break

            try:
                request = json.loads(request)
            except json.JSONDecodeError:
                response = {"status": 400, "response": "Not a valid JSON formatted request."}
                await self.send_to_client(client, json.dumps(response))
                logger.debug(f"{client_name}:{response}\n{request}")
                continue

            logger.debug(f"Server got:\n{request}")

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
                    logger.debug(f"{client_name}:{response}\n{request}")
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
            logger.debug(f"Beginning SEND request from {client_name}")
            await self.send_to_channel_test(f"Client says:{send}")
            await self.send_to_client(client, json.dumps(response))
            logger.debug(f"Done SEND request from {client_name}")

        members = request.get("Members")
        if members is not None:
            logger.debug(f"Beginning MEMBERS request from {client_name}")
            response["Members"] = await self.get_member_activities(members)
            logger.debug(f"Done MEMBERS request from {client_name}, returning {response}")
            await self.send_to_client(client, json.dumps(response))
            logger.debug(f"{client_name} returned members successfully.")

    async def send_to_channel_test(self, message):
        logger.debug(f"Sending {message} to channel.")
        test_channel = self.bot.get_channel(581139962611892229)
        await test_channel.send(message)
        logger.debug(f"Sent {message} to channel!")

    async def get_member_activities(self, members: List[int]) -> Dict[int, str]:
        response_activities = {}
        tortoise_guild = self.bot.get_guild(577192344529404154)
        logger.debug(f"Processing members: {members}")
        for member_id in members:
            logger.debug(f"Processing member: {member_id}")
            member = tortoise_guild.get_member(int(member_id))

            if member is None:
                logger.debug(f"Member {member_id} not found.")
                response_activities[member_id] = "None"
                continue

            activity = member.activity
            if activity is None:
                logger.debug(f"Member {member_id} does not have any activity.")
                response_activities[member_id] = "None"
                continue
            elif activity.type == ActivityType.playing:
                logger.debug(f"Member {member_id} is playing.")
                response_activities[member_id] = f"Playing {activity.name}"
            elif activity.type == ActivityType.streaming:
                logger.debug(f"Member {member_id} is streaming.")
                response_activities[member_id] = f"Streaming {activity}"
            else:
                # For cases where it is None, CustomActivity or Activity(watching, listening)
                logger.debug(activity.type)
                logger.debug(type(activity.type))
                response_activities[member_id] = str(activity)

        logger.debug(f"Processing members done, returning: {response_activities}")
        return response_activities


def setup(bot):
    bot.add_cog(SocketCommunication(bot))
