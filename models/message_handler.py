import asyncio
import logging
import re

import discord
from discord import app_commands
from discord.ext import commands

from models.history_manager import HistoryManager
from models.memory_manager import MemoryManager
from models.sticker_manager import StickerManager
from models.utils import clean_prompt, redact_secrets, smart_split


LOGGER = logging.getLogger(__name__)
MAX_INPUT_CHARS = 3500
STICKER_RE = re.compile(r"<STICKER:([^>\n]{1,80})>")


class MessageHandler:
    def __init__(self, bot: commands.Bot, ai_model, config: dict):
        self.bot = bot
        self.ai = ai_model
        self.config = config
        self.evolution_task = None

    def attach_evolution_task(self, evolution_task) -> None:
        self.evolution_task = evolution_task

    def register_commands(self) -> None:
        @self.bot.event
        async def on_ready():
            try:
                await self.bot.tree.sync()
                LOGGER.info("%s is ready and slash commands are synced.", self.bot.user)
                if self.evolution_task:
                    self.bot.loop.create_task(self.evolution_task.run())
            except Exception:
                LOGGER.exception("Failed during bot startup.")

        @self.bot.event
        async def on_message(message: discord.Message):
            if message.author.bot:
                return

            if not self._channel_allowed(message.channel.id):
                return

            if not self.config.get("respond_to_all_messages", True):
                await self.bot.process_commands(message)
                return

            user_message = self._sanitize_user_input(message.content)
            if not user_message:
                return

            async with message.channel.typing():
                reply_text, sticker_to_send = await self._generate_reply(
                    user_id=str(message.author.id),
                    user_message=user_message,
                    guild=message.guild,
                    include_memory=True,
                    mentioned_users=message.mentions,
                )

            if not reply_text and not sticker_to_send:
                await message.channel.send("我剛剛沒有產生有效回覆，請稍後再試。")
                await self.bot.process_commands(message)
                return

            await self._send_reply(message.channel.send, reply_text, sticker_to_send)
            self._touch_evolution(str(message.author.id), user_message, reply_text)
            await self.bot.process_commands(message)

        @self.bot.tree.command(name="chat", description="和 PhiLia 聊天")
        @app_commands.describe(user_message="想對 PhiLia 說的話")
        async def chat(interaction: discord.Interaction, user_message: str):
            if not self._channel_allowed(interaction.channel_id):
                await interaction.response.send_message(
                    "這個頻道未開放使用 /chat。", ephemeral=True
                )
                return

            cleaned = self._sanitize_user_input(user_message)
            if not cleaned:
                await interaction.response.send_message("請輸入有效內容。", ephemeral=True)
                return

            await interaction.response.defer()
            reply_text, sticker_to_send = await self._generate_reply(
                user_id=str(interaction.user.id),
                user_message=cleaned,
                guild=interaction.guild,
                include_memory=True,
            )
            await self._send_reply(interaction.followup.send, reply_text, sticker_to_send)
            self._touch_evolution(str(interaction.user.id), cleaned, reply_text)

        @self.bot.tree.command(name="reset", description="清除你的聊天歷史")
        async def reset(interaction: discord.Interaction):
            HistoryManager.clear_user(str(interaction.user.id))
            await interaction.response.send_message("你的聊天歷史已清除。", ephemeral=True)

        @self.bot.tree.command(name="force_evolve", description="管理員手動整理自己的記憶")
        async def force_evolve(interaction: discord.Interaction):
            if not self._is_owner(interaction.user.id):
                await interaction.response.send_message("這個指令只有 bot owner 可以使用。", ephemeral=True)
                return

            await interaction.response.defer(ephemeral=True)
            user_id = str(interaction.user.id)
            raw_history = HistoryManager.get_user_history(user_id, max_messages=80)
            if not raw_history:
                await interaction.followup.send("目前沒有可整理的歷史紀錄。")
                return

            processed_count = 0
            chunk_size = 20
            for i in range(0, len(raw_history), chunk_size):
                batch = raw_history[i : i + chunk_size]
                text_block = "\n".join(
                    f"{'User' if msg.get('role') == 'user' else 'AI'}: "
                    f"{(msg.get('parts') or [''])[0]}"
                    for msg in batch
                )
                if self.evolution_task:
                    await self.evolution_task.run_evolution(user_id, text_block)
                    processed_count += 1
                    await asyncio.sleep(2)

            await interaction.followup.send(f"已整理 {processed_count} 批歷史紀錄。")

    async def _generate_reply(
        self,
        *,
        user_id: str,
        user_message: str,
        guild,
        include_memory: bool,
        mentioned_users: list | None = None,
    ) -> tuple[str, object | None]:
        try:
            user_memory = MemoryManager.get_user_memory_str(user_id) if include_memory else ""
            if mentioned_users and self.config.get("allow_mentioned_user_memory", False):
                user_memory += self._mentioned_user_memory(mentioned_users)

            system_instr = self.ai.build_system_instruction(self.config, user_memory=user_memory)
            model_obj = self.ai.start_chat(system_instruction=system_instr)
            history = HistoryManager.get_user_history(
                user_id,
                max_messages=int(self.config.get("max_history_messages", 40)),
            )
            chat_session = model_obj.start_chat(history=history)
            resp = await chat_session.send_message_async(user_message)
            reply_text = clean_prompt(resp.text or "", max_chars=6000)
        except Exception:
            LOGGER.exception("AI generation failed for user %s.", user_id)
            return "抱歉，我剛剛處理訊息時失敗了，請稍後再試。", None

        reply_text, sticker_to_send = self._extract_sticker(reply_text, guild)

        try:
            max_messages = int(self.config.get("max_history_messages", 40))
            HistoryManager.append_message(user_id, "user", user_message, max_messages=max_messages)
            HistoryManager.append_message(user_id, "model", reply_text, max_messages=max_messages)
        except Exception:
            LOGGER.exception("Failed to save history for user %s.", user_id)

        return reply_text, sticker_to_send

    def _sanitize_user_input(self, text: str) -> str:
        return redact_secrets(clean_prompt(text, max_chars=MAX_INPUT_CHARS))

    def _channel_allowed(self, channel_id: int | None) -> bool:
        allowed = self.config.get("allowed_channels", [])
        return not allowed or channel_id in allowed

    def _is_owner(self, user_id: int) -> bool:
        owner_id = str(self.config.get("bot_owner_id", "")).strip()
        return bool(owner_id and str(user_id) == owner_id)

    def _mentioned_user_memory(self, mentioned_users: list) -> str:
        chunks = ["\n\n被提及使用者的記憶，僅供上下文參考，不得外洩："]
        for mentioned_user in mentioned_users[:5]:
            if mentioned_user.bot:
                continue
            memory = MemoryManager.get_user_memory_str(str(mentioned_user.id))
            chunks.append(f"\n[{mentioned_user.display_name}]:\n{memory}")
        return "".join(chunks)

    def _extract_sticker(self, reply_text: str, guild) -> tuple[str, object | None]:
        sticker_map = StickerManager.build_sticker_map(guild)
        sticker_to_send = None
        match = STICKER_RE.search(reply_text)
        if match:
            name = match.group(1).strip()
            sticker_to_send = sticker_map.get(name)
            reply_text = reply_text.replace(match.group(0), "").strip()
        return reply_text, sticker_to_send

    async def _send_reply(self, send_func, reply_text: str, sticker_to_send) -> None:
        if reply_text:
            for part in smart_split(reply_text, limit=1900):
                await send_func(part)
        if sticker_to_send:
            try:
                await send_func(stickers=[sticker_to_send])
            except TypeError:
                LOGGER.info("This Discord send target does not support stickers.")
            except discord.HTTPException:
                LOGGER.exception("Failed to send sticker.")

    def _touch_evolution(self, user_id: str, user_message: str, reply_text: str) -> None:
        if not self.evolution_task:
            return
        try:
            fragment = f"User: {user_message}\nAI: {reply_text}"
            self.evolution_task.touch_user(user_id, fragment)
        except Exception:
            LOGGER.exception("Failed to update evolution buffer for user %s.", user_id)
