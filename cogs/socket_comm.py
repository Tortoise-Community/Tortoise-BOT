import json
import socket
import logging
from sys import stdout
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
        self.tokens = ("abc", "test")
        self.verified_clients = set()
        logger.debug("Starting socket comm...")
        self.bot.loop.create_task(self.run_server(self.get_server()))

    @classmethod
    def get_server(cls):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("0.0.0.0", 15555))
        server.listen(3)
        server.setblocking(False)
        return server

    def cog_unload(self):
        pass

    async def test(self, message):
        logger.debug(f"Sending {message} to channel.")
        test_channel = self.bot.get_channel(581139962611892229)
        await test_channel.send(message)
        logger.debug(f"Sent {message} to channel!")

    async def handle_client(self, client):
        request = None
        client_name = client.getpeername()
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

            if client_name not in self.verified_clients:
                token = request.get("Auth")
                if token is not None and token in self.tokens:
                    self.verified_clients.add(client_name)
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
            await self.bot.loop.sock_sendall(client, bytes(msg.encode("utf8")))
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

        send = request.get("Send")
        if send is not None:
            logger.debug(f"Beginning SEND request from {client_name}")
            await self.test(f"Client says:{send}")
            response = {"status": 200}
            await self.send_to_client(client, json.dumps(response))
            logger.debug(f"Done SEND request from {client_name}")

        members = request.get("Members")
        if members is not None:
            logger.debug(f"Beginning MEMBERS request from {client_name}")
            response_activities = {}
            tortoise_guild = self.bot.get_guild(577192344529404154)
            for member_id in members:
                member = tortoise_guild.get_member(int(member_id))
                if member is None:
                    response_activities[member_id] = "None"
                    continue

                activity = member.activity
                if activity is None:
                    response_activities[member_id] = "None"
                    continue
                elif activity.type == ActivityType.playing:
                    response_activities[member_id] = f"Playing {activity.name}"
                elif activity.type == ActivityType.streaming:
                    response_activities[member_id] = f"Streaming {activity}"
                else:
                    # For cases where it is None, CustomActivity or Activity(watching, listening)
                    logger.debug(activity.type)
                    logger.debug(type(activity.type))
                    response_activities[member_id] = str(activity)

            response = {"status": 200, "Members": response_activities}
            logger.debug(f"Done MEMBERS request from {client_name}, returning {response}")
            await self.send_to_client(client, json.dumps(response))
            logger.debug(f"{client_name} returned members successfully.")

    async def run_server(self, server: socket.socket):
        while True:
            client, _ = await self.bot.loop.sock_accept(server)
            logger.info(f"{client.getpeername()} connected.")
            self.bot.loop.create_task(self.handle_client(client))


def setup(bot):
    bot.add_cog(SocketCommunication(bot))