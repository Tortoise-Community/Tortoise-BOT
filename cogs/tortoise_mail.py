import discord
from discord.ext import commands
from asyncio import TimeoutError
from typing import Union


mod_mail_report_channel_id = 581139962611892229
code_submissions_channel_id = 581139962611892229
bug_reports_channel_id = 581139962611892229


class UnsupportedFileExtension(Exception):
    pass


class UnsupportedFileEncoding(ValueError):
    pass


class ModMail(commands.Cog):
    """
    Only one guild supported.

    TODO:
    Check if emoji id error deleted.
    Check if user blocks dms.
    Add timeout so user can't spam.
    Prettify with embeds.
    Delete message saying user submitted mod mail request after it's accepted by admin? Or
    just add a command to list current pending ones.
    """
    def __init__(self, bot):
        self.bot = bot
        # Key is user id value is mod/admin id
        self.active_mod_mails = {}
        self.pending_mod_mails = set()
        self.active_event_submissions = set()
        self.active_bug_reports = set()
        # Keys are custom emoji IDs, subdict message is the message appearing in the bot DM and callable
        # is the method to call when that option is selected.
        self._options = {620502308815503380: {"message": "Mod mail", "callable": self.create_mod_mail},
                         611403448750964746: {"message": "Event submission", "callable": self.create_event_submission},
                         610825682070798359: {"message": "Bug report", "callable": self.create_bug_report}}
        # User IDs for which the trigger_typing() is active, so we don't spam the method.
        self._typing_active = set()

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        user_id = payload.user_id
        if user_id == self.bot.user.id:
            # Ignore the bot
            return
        elif self.is_any_session_active(user_id):
            return

        for emoji_id, sub_dict in self._options.items():
            emoji = self.bot.get_emoji(emoji_id)
            if emoji == payload.emoji:
                user = self.bot.get_user(user_id)
                await sub_dict["callable"](user)
                break

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        elif message.guild is not None:
            # Functionality only active in DMs
            return

        if self.is_any_session_active(message.author.id):
            return
        else:
            await self.send_dm_options(output=message.author)

    @commands.Cog.listener()
    async def on_typing(self, channel, user, when):
        if not isinstance(channel, discord.DMChannel):
            return
        elif not self.is_any_session_active(user.id):
            return
        elif user.id in self._typing_active:
            return

        destination_id = self.active_mod_mails.get(user.id)
        if destination_id is None:
            # If it's None there is no user with that ID that has opened mod mail request.
            # However we can still have the mod/admin that could be attending mod mail
            destination_id = self._get_dict_key_by_value(user.id)
            if destination_id is None:
                # If it's again None then there is no such ID in either user nor mods/admins
                return

        self._typing_active.add(user.id)
        destination_user = self.bot.get_user(destination_id)
        # Per docs: Active for 10s or until first message
        await destination_user.trigger_typing()
        self._typing_active.remove(user.id)

    def _get_dict_key_by_value(self, value: int) ->int:
        for key, v in self.active_mod_mails.items():
            if v == value:
                return key

    async def send_dm_options(self, *, output):
        for emoji_id, sub_dict in self._options.items():
            dm_msg = await output.send(sub_dict["message"])
            await dm_msg.add_reaction(self.bot.get_emoji(emoji_id))

    def is_any_session_active(self, user_id: int) -> bool:
        # If the mod mail or anything else is active don't clutter the active session
        return any(user_id in active for active in (self.active_mod_mails.keys(),
                                                    self.active_mod_mails.values(),
                                                    self.active_event_submissions,
                                                    self.active_bug_reports))

    async def create_mod_mail(self, user: discord.User):
        if user.id in self.pending_mod_mails:
            await user.send("You already have a pending mod mail, please be patient.")
            return

        mod_mail_report_channel = self.bot.get_channel(mod_mail_report_channel_id)
        await mod_mail_report_channel.send(f"User `{user.name}` ID:{user.id} submitted for mod mail.")
        self.pending_mod_mails.add(user.id)
        await user.send("Mod mail was sent to admins, please wait for on of the admins to accept.")

    async def create_event_submission(self, user: discord.User):
        user_reply = await self._wait_for(self.active_event_submissions, user)
        if user_reply is None:
            return

        try:
            possible_attachment = await self.get_message_txt_attachment(user_reply)
        except (UnsupportedFileExtension, UnsupportedFileEncoding) as e:
            await user.send(f"Error: {e} , canceling.")
            self.active_event_submissions.remove(user.id)
            return

        event_submission = user_reply.content if possible_attachment is None else possible_attachment
        if len(event_submission) < 10:
            await user.send("Too short - seems invalid, canceling.")
            self.active_event_submissions.remove(user.id)
            return

        code_submissions_channel = self.bot.get_channel(code_submissions_channel_id)
        await code_submissions_channel.send(f"User `{user.name}` ID:{user.id} submitted code submission: "
                                            f"{event_submission}")
        await user.send("Event submission successfully submitted.")
        self.active_event_submissions.remove(user.id)

    async def create_bug_report(self, user: discord.User):
        user_reply = await self._wait_for(self.active_bug_reports, user)
        if user_reply is None:
            return

        try:
            possible_attachment = await self.get_message_txt_attachment(user_reply)
        except (UnsupportedFileExtension, UnsupportedFileEncoding) as e:
            await user.send(f"Error: {e} , canceling.")
            self.active_bug_reports.remove(user.id)
            return

        bug_report = user_reply.content if possible_attachment is None else possible_attachment
        if len(bug_report) < 10:
            await user.send("Too short - seems invalid, canceling.")
            self.active_bug_reports.remove(user.id)
            return

        bug_report_channel = self.bot.get_channel(bug_reports_channel_id)
        await bug_report_channel.send(f"User `{user.name}` ID:{user.id} submitted bug report: {bug_report}")
        await user.send("Bug report successfully submitted, thank you.")
        self.active_bug_reports.remove(user.id)

    async def _wait_for(self, container: set, user: discord.User) -> Union[discord.Message, None]:
        """
        Simple custom wait_for that waits for user reply for 5 minutes and has ability to cancel the wait,
        deal with errors and deal with containers (which mark users that are currently doing something aka
        event submission/bug report etc).
        :param container: set, container holding active user sessions by having their IDs in it.
        :param user: Discord user to wait reply from
        :return: Union[Message, None] message representing user reply, can be none representing invalid reply.
        """
        def check(msg):
            return msg.guild is None and msg.author == user

        container.add(user.id)
        await user.send("Reply with message, link to paste service or uploading utf-8 `.txt` file.\n"
                        "You have 5m, type `cancel` to cancel right away.")

        try:
            user_reply = await self.bot.wait_for("message", check=check, timeout=300)
        except TimeoutError:
            await user.send("You took too long to reply.")
            container.remove(user.id)
            return

        if user_reply.content.lower() == "cancel":
            await user.send("Successfully canceled.")
            container.remove(user.id)
            return

        return user_reply

    @classmethod
    async def get_message_txt_attachment(cls, message: discord.Message) -> Union[str, None]:
        """
        Only supports .txt file attachments and only utf-8 encoding supported.
        :param message: message object to extract attachment from.
        :return: Union[str, None]
        :raise UnsupportedFileExtension: If file type is other than .txt
        :raise UnicodeDecodeError: If decoding the file fails
        """
        try:
            attachment = message.attachments[0]
        except IndexError:
            return None

        if not attachment.filename.endswith(".txt"):
            raise UnsupportedFileExtension("Only `.txt` files supported")

        try:
            content = (await attachment.read()).decode("utf-8")
        except UnicodeDecodeError:
            raise UnsupportedFileEncoding("Unsupported file encoding, please only use utf-8")

        return content

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def attend(self, ctx, user_id: int):
        # Time to wait for FIRST USER reply. Useful if mod attends but user is away.
        first_timeout = 10_800
        # Flag for above variable. False means there has been no messages from the user.
        first_timeout_flag = False
        # After the user sends first reply this is the timeout we use.
        regular_timeout = 600

        user = self.bot.get_user(user_id)
        mod = ctx.author

        if user is None:
            await ctx.send("That user cannot be found or you entered incorrect ID.")
            return
        elif user_id not in self.pending_mod_mails:
            await ctx.send("That user is not registered for mod mail.")
            return
        elif self.is_any_session_active(mod.id):
            await ctx.send("You already have one of active sessions (reports/mod mail etc).")
            return

        self.pending_mod_mails.remove(user_id)
        self.active_mod_mails[user_id] = mod.id

        await user.send(f"`{mod.name}` has accepted your mod mail request. Replying here in DM will transfer "
                        f"messages directly to him. Type `close` to close this mod mail.")
        await mod.send(f"`You have accepted {user.name}` mod mail request. Replying here in DM will transfer "
                       f"messages directly to them. Type `close` to close this mod mail.")
        await ctx.send("Mod mail initialized, check your DMs.", delete_after=10)

        def mod_mail_check(msg):
            return msg.guild is None and msg.author.id in (user_id, mod.id)

        _timeout = first_timeout

        while True:
            try:
                mail_msg = await self.bot.wait_for("message", check=mod_mail_check, timeout=_timeout)
            except TimeoutError:
                timeout_msg = "Mod mail closed due to inactivity."
                await mod.send(timeout_msg)
                await user.send(timeout_msg)
                break

            # Deal with dynamic timeout.
            if mail_msg.author == user and not first_timeout_flag:
                first_timeout_flag = True
                _timeout = regular_timeout

            # Deal with canceling mod mail
            if mail_msg.content.lower() == "close":
                close_msg = "Mod mail successfully closed."
                await mod.send(close_msg)
                await user.send(close_msg)
                del self.active_mod_mails[user_id]
                break

            # Deal with user-mod communication
            if mail_msg.author == user:
                await mod.send(f"{user.name} says:{mail_msg.content}")
            elif mail_msg.author == mod:
                await user.send(f"{mod.name} says:{mail_msg.content}")


def setup(bot):
    bot.add_cog(ModMail(bot))
