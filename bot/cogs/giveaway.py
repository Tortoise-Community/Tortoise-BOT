from __future__ import annotations
import asyncio
import random
import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

import discord
from discord.ext import commands
from discord import app_commands

from bot.utils.embed_handler import info, warning, success
from bot.utils.checks import check_if_tortoise_staff


class QuestionModal(discord.ui.Modal, title='Add Question'):
    question = discord.ui.TextInput(label='Question', max_length=200)
    expected = discord.ui.TextInput(label='Expected Answer (yes/no)', max_length=3, placeholder='yes')

    def __init__(self, parent: SetupView):
        super().__init__()
        self.parent = parent

    async def on_submit(self, interaction: discord.Interaction):
        ans = self.expected.value.lower().strip()
        if ans not in ('yes', 'no'):
            await interaction.response.send_message('Expected answer must be "yes" or "no".', ephemeral=True)
            return

        self.parent.questions.append({'question': self.question.value, 'answer': ans})
        await interaction.response.send_message(f'Question added. Total: {len(self.parent.questions)}', ephemeral=True)


class SetupView(discord.ui.View):
    def __init__(self, cog: Giveaway, data: dict):
        super().__init__(timeout=600)
        self.cog = cog
        self.data = data
        self.questions: List[Dict[str, str]] = []

    @discord.ui.button(label='Add Question', style=discord.ButtonStyle.blurple)
    async def add_question(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuestionModal(self))

    @discord.ui.button(label='Publish Giveaway', style=discord.ButtonStyle.green)
    async def publish(self, interaction: discord.Interaction, button: discord.ui.Button):
        end_time = datetime.now(timezone.utc) + timedelta(minutes=self.data['duration'])
        timestamp = int(end_time.timestamp())

        description_body = (
            f"**{self.data['name']}**\n"
            f"{self.data['description']}\n\n"
            f"**Prizes**\n{self.data['prizes']}\n\n"
            f"Ends: <t:{timestamp}:R>"
        )

        embed = info(description_body, interaction.client.user, '🎉 Giveaway Started')
        msg = await interaction.channel.send(embed=embed, view=JoinView(self.cog))

        # Persist to DB
        await self.cog.manager.create_giveaway(
            msg.id, interaction.guild.id, interaction.channel.id,
            interaction.user.id, self.data['name'], self.data['description'],
            self.data['prizes'], json.dumps(self.questions),
            self.data['winners'], end_time
        )

        # Start the background timer
        self.cog.tasks[msg.id] = asyncio.create_task(self.cog.finish_task(msg.id, end_time))

        await interaction.response.edit_message(content='✅ Giveaway published successfully.', view=None)


class CreateModal(discord.ui.Modal, title='Create Giveaway'):
    name = discord.ui.TextInput(label='Name', placeholder='Epic Nitro Giveaway')
    description = discord.ui.TextInput(label='Description', style=discord.TextStyle.paragraph, required=False)
    prizes = discord.ui.TextInput(label='Prizes', style=discord.TextStyle.paragraph, placeholder='1x Discord Nitro')

    def __init__(self, cog: Giveaway, duration: int, winners: int):
        super().__init__()
        self.cog = cog
        self.duration = duration
        self.winners = winners

    async def on_submit(self, interaction: discord.Interaction):
        data = {
            'name': self.name.value,
            'description': self.description.value,
            'prizes': self.prizes.value,
            'duration': self.duration,
            'winners': self.winners
        }
        await interaction.response.send_message(
            'Giveaway initialized. Add optional qualification questions below.',
            view=SetupView(self.cog, data),
            ephemeral=True
        )


class Questionnaire(discord.ui.View):
    def __init__(self, cog: Giveaway, row: dict, user_id: int):
        super().__init__(timeout=300)
        self.cog = cog
        self.row = row
        self.user_id = user_id
        self.current_index = 0
        self.questions = row['questions']

    async def _update_question(self, interaction: discord.Interaction):
        q_data = self.questions[self.current_index]
        embed = info(q_data['question'], self.cog.bot.user, f'Question {self.current_index + 1}/{len(self.questions)}')
        await interaction.response.edit_message(embed=embed, view=self)

    async def handle_answer(self, interaction: discord.Interaction, ans: str):
        if interaction.user.id != self.user_id:
            return await interaction.response.send_message('This is not your session.', ephemeral=True)

        # Validate answer
        if ans != self.questions[self.current_index]['answer']:
            await interaction.response.edit_message(
                embed=warning("You do not qualify for this giveaway based on your answers."),
                view=None
            )
            return

        self.current_index += 1

        # Check if finished
        if self.current_index >= len(self.questions):
            success_joined = await self.cog.manager.enter(self.row['message_id'], self.user_id)
            if success_joined:
                try:
                    await self.cog.bot.sys_log_channel.send(embed=info(
                       f"{interaction.user.mention} joined the giveaway.", self.cog.bot.user, ""
                    ))
                except Exception as e:
                    pass
            msg = 'Entry successful! Good luck.' if success_joined else 'You have already entered this giveaway.'
            await interaction.response.edit_message(embed=success(msg), view=None)
        else:
            await self._update_question(interaction)

    @discord.ui.button(label='Yes', style=discord.ButtonStyle.green)
    async def yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 'yes')

    @discord.ui.button(label='No', style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_answer(interaction, 'no')


class JoinView(discord.ui.View):
    def __init__(self, cog: Giveaway, disabled: bool = False):
        super().__init__(timeout=None)
        self.cog = cog
        self.join_btn.disabled = disabled

    @discord.ui.button(label="🎉 Join Giveaway", style=discord.ButtonStyle.primary, custom_id="join_giveaway_dynamic")
    async def join_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        row = await self.cog.manager.get_active(interaction.message.id)
        if not row:
            return await interaction.response.send_message(embed=warning("This giveaway has ended."), ephemeral=True)

        questions = self._normalize_questions(row.get("questions"))

        if not questions:
            joined = await self.cog.manager.enter(row["message_id"], interaction.user.id)
            if joined:
                try:
                    await self.cog.bot.sys_log_channel.send(embed=info(
                       f"{interaction.user.mention} joined the giveaway.", self.cog.bot.user, ""
                    ))
                except Exception as e:
                    pass
            embed = success("You joined the giveaway!") if joined else warning("You already joined this giveaway.")
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        row_dict = dict(row)
        row_dict["questions"] = questions
        view = Questionnaire(self.cog, row_dict, interaction.user.id)

        await interaction.response.send_message(
            embed=info(questions[0]["question"], self.cog.bot.user, f"Question 1/{len(questions)}"),
            view=view,
            ephemeral=True
        )

    def _normalize_questions(self, raw) -> list:
        if not raw: return []
        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
            if not isinstance(data, list): return []

            normalized = []
            for item in data:
                if isinstance(item, dict) and "question" in item:
                    normalized.append({"question": item["question"], "answer": item.get("answer", "yes").lower()})
            return normalized
        except (json.JSONDecodeError, TypeError):
            return []


class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.manager = bot.giveaway_manager
        self.tasks: Dict[int, asyncio.Task] = {}
        self.bot.add_view(JoinView(self))

    async def cog_load(self):
        """Restart background tasks for pending giveaways on reboot."""
        pending = await self.manager.get_pending()
        for row in pending:
            self.tasks[row['message_id']] = asyncio.create_task(
                self.finish_task(row['message_id'], row['ends_at'])
            )

    @app_commands.command(name='giveaway_create', description='Start a new giveaway')
    @app_commands.describe(duration_minutes="How long the giveaway lasts", winners="Number of winners to pick")
    @app_commands.check(check_if_tortoise_staff)
    async def giveaway_create(
            self,
            interaction: discord.Interaction,
            duration_minutes: app_commands.Range[int, 1, 21600],
            winners: app_commands.Range[int, 1, 10] = 1
    ):
        await interaction.response.send_modal(CreateModal(self, duration_minutes, winners))

    async def finish_task(self, message_id: int, end_time: datetime):
        # Wait until expiry
        delay = (end_time - datetime.now(timezone.utc)).total_seconds()
        if delay > 0:
            await asyncio.sleep(delay)

        row = await self.manager.get_active(message_id)
        if not row:
            return

        entries = await self.manager.get_entries(message_id)
        winner_count = min(len(entries), row['winners'])
        picks = random.sample(entries, winner_count) if entries else []

        await self.manager.finish(message_id, picks)

        # Update the original message
        guild = self.bot.get_guild(row['guild_id'])
        if not guild: return

        channel = guild.get_channel(row['channel_id'])
        if not channel: return

        try:
            msg = await channel.fetch_message(message_id)
            winner_mentions = ', '.join(f'<@{u}>' for u in picks) if picks else 'No valid entries.'

            result_text = (
                f"**{row['name']}**\n"
                f"{row['description']}\n\n"
                f"**Prizes**\n{row['prizes']}\n\n"
                f"**Winners**\n{winner_mentions}"
            )

            end_embed = info(result_text, self.bot.user, '🎉 Giveaway Ended')
            await msg.edit(embed=end_embed, view=JoinView(self, disabled=True))
        except discord.NotFound:
            pass
        except Exception as e:
            print(f"Error finishing giveaway {message_id}: {e}")


async def setup(bot):
    await bot.add_cog(Giveaway(bot))
