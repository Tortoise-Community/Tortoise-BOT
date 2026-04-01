import logging
from io import StringIO
from typing import Union
from asyncio import TimeoutError

import discord
from discord.ext import commands

from bot import constants
from bot.utils.cooldown import CoolDown
from bot.utils.message_logger import MessageLogger
from bot.utils.embed_handler import authored, failure, success, info, create_suggestion_msg, authored_sm


logger = logging.getLogger(__name__)


class UnsupportedFileExtension(Exception):
    pass


class UnsupportedFileEncoding(ValueError):
    pass

class DMInitView(discord.ui.View):
    def __init__(self, cog: "TortoiseDM", user: discord.User):
        super().__init__(timeout=300)
        self.cog = cog
        self.user = user

        for i, (emoji_id, sub_dict) in enumerate(cog._options.items()):
            if not sub_dict["check"]():
                continue

            emoji = cog.bot.get_emoji(emoji_id)
            if emoji is None:
                continue

            self.add_item(DMInitButton(
                emoji=emoji,
                label=sub_dict["message"],
                callback_func=sub_dict["callable"],
                row=i
            ))


class DMInitButton(discord.ui.Button):
    def __init__(self, emoji, label, callback_func, row):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            emoji=emoji,
            label=label,
            row=row
        )
        self.callback_func = callback_func

    async def callback(self, interaction: discord.Interaction):
        user = interaction.user
        cog = interaction.client.get_cog("TortoiseDM")

        # Remove buttons immediately
        if interaction.message:
            view = self.view
            view.clear_items()
            await interaction.message.edit(view=view)

        if cog.is_any_session_active(user.id):
            await interaction.response.send_message("Session already active.", ephemeral=True)
            return

        if cog.cool_down.is_on_cool_down(user.id):
            msg = f"You are on cooldown. You can retry after {cog.cool_down.retry_after(user.id)}s"
            await interaction.response.send_message(embed=failure(msg), ephemeral=True)
            return
        else:
            cog.cool_down.add_to_cool_down(user.id)

        await interaction.response.defer(ephemeral=True)
        await self.callback_func(user)


class ModMailAcceptView(discord.ui.View):
    def __init__(self, cog: "TortoiseDM", user_id: int):
        super().__init__(timeout=None)
        self.cog = cog
        self.user_id = user_id

    @discord.ui.button(label="Accept Mod Mail", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        mod = interaction.user
        user_id = self.user_id

        if not any(role in mod.roles for role in (self.cog.admin_role, self.cog.moderator_role)):
            await interaction.response.send_message("No permission.", ephemeral=True)
            return

        if user_id not in self.cog.pending_mod_mails:
            await interaction.response.send_message("Mod mail no longer pending.", ephemeral=True)
            return

        user = self.cog.bot.get_user(user_id)
        if user is None:
            await interaction.response.send_message("User not found.", ephemeral=True)
            return

        self.clear_items()
        await self.cog.update_staff_embed_from_message(
            interaction.message,
            footer_append=f"☑️ Accepted by {mod.name}",
            color=discord.Color.green(),
            view=self
        )


        try:
            await mod.send(
                embed=success(
                    f"You have accepted `{user}` mod mail request.\n"
                    "Reply here in DMs to chat with them.\n"
                    "This mod mail will be logged.\n"
                    "Type `close` to close this mod mail."
                )
            )
        except discord.HTTPException:
            await interaction.followup.send("Mod mail failed: moderator DMs closed.", ephemeral=True)
            return

        await user.send(
            embed=authored(
                (
                    f"{mod.name} has accepted your mod mail request.\n"
                    "Reply here in DMs to chat with them.\n"
                    "This mod mail will be logged, by continuing you agree to that."
                ),
                author=mod
            )
        )

        self.cog.pending_mod_mails.remove(user_id)
        self.cog.active_mod_mails[user_id] = mod.id
        embed = success("Mod Mail initialized. Check your DMs")
        await interaction.response.send_message(embed=embed, ephemeral=True)


        first_timeout = 21_600
        regular_timeout = 1800
        first_timeout_flag = False
        _timeout = first_timeout

        log = MessageLogger(mod.id, user.id)

        def mod_mail_check(msg):
            return msg.guild is None and msg.author.id in (user_id, mod.id)

        while True:
            try:
                mail_msg = await self.cog.bot.wait_for("message", check=mod_mail_check, timeout=_timeout)
                log.add_message(mail_msg)
            except TimeoutError:
                timeout_embed = failure("Mod mail closed due to inactivity.")
                log.add_embed(timeout_embed)
                await mod.send(embed=timeout_embed)
                await user.send(embed=timeout_embed)
                del self.cog.active_mod_mails[user_id]
                logs = await self.cog.mod_mail_report_channel.send(
                    file=discord.File(StringIO(str(log)), filename=log.filename)
                )

                await self.cog.update_staff_embed(
                    user_id,
                    description=logs.jump_url,
                    footer_append="🕑 Closed due to inactivity.",
                    color=discord.Color.dark_red()
                )

                del self.cog.modmail_messages[user_id]
                break

            attachments = self.cog._get_attachments_as_urls(mail_msg)
            mail_msg.content += attachments

            if len(mail_msg.content) > 1900:
                mail_msg.content = f"{mail_msg.content[:1900]} ...truncated because it was too long."

            if mail_msg.author == user and not first_timeout_flag:
                first_timeout_flag = True
                _timeout = regular_timeout

            if mail_msg.content.lower() == "close" and mail_msg.author.id == mod.id:
                close_embed = success(f"Mod mail successfully closed by {mail_msg.author}.")
                log.add_embed(close_embed)
                await mod.send(embed=close_embed)
                await user.send(embed=close_embed)
                del self.cog.active_mod_mails[user_id]
                logs = await self.cog.mod_mail_report_channel.send(
                    file=discord.File(StringIO(str(log)), filename=log.filename)
                )
                await self.cog.update_staff_embed(
                    user_id,
                    description=logs.jump_url,
                    footer_append="✅ Session Completed",
                    color=discord.Color.dark_grey()
                )
                del self.cog.modmail_messages[user_id]
                break

            if mail_msg.author == user:
                await mod.send(mail_msg.content)
            elif mail_msg.author == mod:
                await user.send(mail_msg.content)


class TortoiseDM(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._tortoise_guild = None
        self._admin_role = None
        self._moderator_role = None
        self.cool_down = CoolDown(seconds=120)
        self.bot.loop.create_task(self.cool_down.start())

        # Key is user id value is mod/admin id
        self.active_mod_mails = {}
        self.modmail_messages = {}
        self.pending_mod_mails = set()
        self.active_event_submissions = set()
        self.active_bug_reports = set()
        self.active_suggestions = set()
        self.active_staff_applications = set()

        # Keys are custom emoji IDs, sub-dict message is the message appearing in the bot DM,
        # callable is the method to call when that option is selected and check is callable that returns
        # bool whether that option is disabled or not.
        # TODO if callable errors container will not be properly updated so users will not be able to call it again
        self._options = {
            constants.mod_mail_emoji_id: {
                "message": "Contact staff (Mod Mail)",
                "callable": self.create_mod_mail,
                "check": lambda: self.bot.tortoise_meta_cache["mod_mail"]
            },
            constants.event_emoji_id: {
                "message": "Event submission",
                "callable": self.create_event_submission,
                "check": lambda: self.bot.tortoise_meta_cache["event_submission"]
            },
            constants.staff_application_emoji_id: {
                "message": "Staff Application",
                "callable": self.create_staff_application,
                "check": lambda: self.bot.tortoise_meta_cache["staff_application"]
            },
            constants.bug_emoji_id: {
                "message": "Bug report",
                "callable": self.create_bug_report,
                "check": lambda: self.bot.tortoise_meta_cache["bug_report"]
            },
            constants.suggestions_emoji_id: {
                "message": "Make a suggestion",
                "callable": self.create_suggestion,
                "check": lambda: self.bot.tortoise_meta_cache["suggestions"]
            }
        }

        # User IDs for which the trigger_typing() is active, so we don't spam the method.
        self._typing_active = set()
        self.bug_report_channel = None
        self.user_suggestions_channel = None
        self.mod_mail_report_channel = None
        self.code_submissions_channel = None
        self.staff_applications_channel= None
        self.staff_channel = None

    @commands.Cog.listener()
    async def on_ready(self):
        # Server Utility Channels
        self.bug_report_channel = self.bot.get_channel(constants.bug_reports_channel_id)
        self.user_suggestions_channel = self.bot.get_channel(constants.suggestions_channel_id)
        self.mod_mail_report_channel = self.bot.get_channel(constants.mod_mail_report_channel_id)
        self.code_submissions_channel = self.bot.get_channel(constants.code_submissions_channel_id)
        self.staff_channel = self.bot.get_channel(constants.staff_channel_id)
        self.staff_applications_channel = self.bot.get_channel(constants.system_log_channel_id)

    @property
    def tortoise_guild(self):
        if self._tortoise_guild is None:
            self._tortoise_guild = self.bot.get_guild(constants.tortoise_guild_id)
        return self._tortoise_guild

    @property
    def admin_role(self):
        if self._admin_role is None:
            self._admin_role = self.tortoise_guild.get_role(constants.admin_role_id)
        return self._admin_role

    @property
    def moderator_role(self):
        if self._moderator_role is None:
            self._moderator_role = self.tortoise_guild.get_role(constants.moderator_role_id)
        return self._moderator_role

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        elif message.guild is not None:
            return  # Functionality only active in DMs
        if self.is_any_session_active(message.author.id):
            return
        else:
            await self.send_dm_options(output=message.author)

    @commands.Cog.listener()
    async def on_typing(self, channel, user, _when):
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

        if destination_user is None:
            destination_user = await self.bot.fetch_user(destination_id)

        dm = destination_user.dm_channel

        if dm is None:
            dm = await destination_user.create_dm()
        # Per docs: Active for 10s or until first message
        async with dm.typing():
            pass
        self._typing_active.remove(user.id)

    def _get_dict_key_by_value(self, value: int) -> int:
        for key, v in self.active_mod_mails.items():
            if v == value:
                return key

    async def send_dm_options(self, *, output):
        if not any(sub_dict["check"]() for sub_dict in self._options.values()):
            return

        embed = discord.Embed(description="Select an option below to continue.\nUse the buttons to proceed.")
        embed.set_footer(text="Tortoise Community")

        view = DMInitView(self, output)
        await output.send(embed=embed, view=view)


    def is_any_session_active(self, user_id: int) -> bool:
        return any(
            user_id in active for active in (
                self.active_mod_mails.keys(),
                self.active_mod_mails.values(),
                self.active_event_submissions,
                self.active_bug_reports,
                self.active_suggestions,
                self.active_staff_applications,
            )
        )

    def _apply_staff_embed_updates(
            self,
            embed: discord.Embed,
            *,
            footer_append=None,
            description=None,
            color=None
    ):
        if description is not None:
            embed.description = description

        if footer_append:
            current = embed.footer.text if embed.footer else ""
            embed.set_footer(
                text=f"{current}\n\n{footer_append}" if current else footer_append
            )

        if color:
            embed.color = color

        return embed

    async def update_staff_embed_from_message(
            self,
            message: discord.Message,
            *,
            footer_append=None,
            description=None,
            color=None,
            view=None
    ):
        embed = message.embeds[0]

        embed = self._apply_staff_embed_updates(
            embed,
            footer_append=footer_append,
            description=description,
            color=color
        )

        await message.edit(embed=embed, view=view)

    async def update_staff_embed(
            self,
            user_id: int,
            *,
            footer_append=None,
            description=None,
            color=None
    ):
        message_id = self.modmail_messages.get(user_id)
        if not message_id:
            return

        try:
            msg = await self.staff_channel.fetch_message(message_id)

            await self.update_staff_embed_from_message(
                msg,
                footer_append=footer_append,
                description=description,
                color=color
            )

        except Exception:
            pass

    async def create_mod_mail(self, user: discord.User, source: str = "dm"):
        if user.id in self.pending_mod_mails:
            await user.send(embed=failure("You already have a pending mod mail, please be patient."))
            return

        source_text = {
            "dm": "submitted for mod mail.",
            "panel": "created a ban appeal request."
        }.get(source, source)

        submission_embed = authored_sm(f"{user.name} {source_text}", author=user)
        view = ModMailAcceptView(self, user.id)

        await self.staff_channel.send("@here", delete_after=30)
        msg = await self.staff_channel.send(
            embed=submission_embed,
            view=view
        )
        self.modmail_messages[user.id] = msg.id
        self.pending_mod_mails.add(user.id)
        if source == "dm":
            embed = info("Mail is initialized and the moderators have been contacted.\n"
                         "You'll be notified once someone from the team responds.",
                         user, "ModMail Created!")
            embed.set_footer(
                text="NOTE: Response time may vary; No need to wait here."
            )
            await user.send(embed=embed)

    async def create_event_submission(self, user: discord.User):
        user_reply = await self._get_user_reply(self.active_event_submissions, user, "Event Submission")
        if user_reply is None:
            return

        await self.code_submissions_channel.send(
            f"User `{user}` ID:{user.id} submitted code submission: "
            f"{user_reply}"
        )
        await user.send(embed=success("Event submission successfully submitted."))
        self.active_event_submissions.remove(user.id)

    async def create_staff_application(self, user: discord.User):
        submission_format = ("```ex\n"
                             "Name: Your name.\n"
                             "Role: The role you are apply for.\n"
                             "Timezone: Your timezone. \n"
                             "About:  Tell us a bit about yourself.\n"
                             "Reason:  Why are you a good fit for this role??```\n"
                             "**Other details (Optional)** \n"
                             " - How long are you active on discord per day.\n"
                             " - When did you join discord. \n"
                             " - Any previous experience.")

        user_reply = await self._get_user_reply(
            self.active_staff_applications,
            user, "Staff Application",
            submission_format
        )
        if user_reply is None:
            return

        await self.staff_applications_channel.send(embed=info(
            f"User {user.mention} submitted staff application: \n"
            f"{user_reply}", self.bot.user, "Staff Application", f"ID: {user.id}")
        )
        await user.send(embed=success("Staff application successfully submitted."))
        self.active_staff_applications.remove(user.id)

    async def create_bug_report(self, user: discord.User):
        user_reply = await self._get_user_reply(self.active_bug_reports, user, "Bug Report")
        if user_reply is None:
            return

        await self.bug_report_channel.send(f"User `{user}` ID:{user.id} submitted bug report: {user_reply}")
        await user.send(embed=success("Bug report successfully submitted, thank you."))
        self.active_bug_reports.remove(user.id)

    async def create_suggestion(self, user: discord.User):
        user_reply = await self._get_user_reply(self.active_suggestions, user, "Suggestion")
        if user_reply is None:
            return

        msg = await create_suggestion_msg(self.user_suggestions_channel, user, user_reply)
        await self.bot.api_client.post_suggestion(user, msg, user_reply)
        await user.send(embed=success("Suggestion successfully submitted, thank you."))
        self.active_suggestions.remove(user.id)

    async def _get_user_reply(self, container: set, user: discord.User, sub_type: str, sub_format=None) -> Union[str, None]:
        """
        Helper method to get user reply, only deals with errors.
        Uses self._wait_for method so it can get both the user message reply and text from attachment file.
        :param container: set, container holding active user sessions by having their IDs in it.
        :param user: Discord user to wait reply from
        :return: Union[str, None] string representing user reply, can be None representing invalid reply.
        """
        user_reply = await self._wait_for(container, user, sub_type, sub_format)

        if user_reply is None:
            return None

        try:
            possible_attachment = await self.get_message_txt_attachment(user_reply)
        except (UnsupportedFileExtension, UnsupportedFileEncoding) as e:
            container.remove(user.id)
            await user.send(embed=failure(f"Error: {e} , canceling."))
            return

        user_reply_content = user_reply.content if possible_attachment is None else possible_attachment

        if len(user_reply_content) < 10:
            container.remove(user.id)
            await user.send(embed=failure("Too short - seems invalid, canceling."))
            return None
        else:
            return user_reply_content

    async def _wait_for(self, container: set, user: discord.User, sub_type: str, sub_format = None) -> Union[discord.Message, None]:
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

        if sub_format is not None:
            sub_format = "\n" + sub_format

        await user.send(embed=info(
            f"Reply with single message or link to paste service or upload a `.txt` file.\n"
            f"Type `cancel` to cancel right away. "
            f"\n\n{'**Format: **' + sub_format if sub_format else ''}",
            user, sub_type + " Initialized", "This submission will timeout in 5 minutes.")
        )

        try:
            user_reply = await self.bot.wait_for("message", check=check, timeout=300)
        except TimeoutError:
            container.remove(user.id)
            await user.send(embed=failure("Submission timed out."))
            return

        if user_reply.content.lower() == "cancel":
            container.remove(user.id)
            await user.send(embed=success("Successfully canceled."))
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

    @classmethod
    def _get_attachments_as_urls(cls, message: discord.Message) -> str:
        if not message.attachments:
            return ""

        urls = '\n'.join(attachment.url for attachment in message.attachments)
        return f"\nAttachments:\n{urls}"


async def setup(bot):
    await bot.add_cog(TortoiseDM(bot))
