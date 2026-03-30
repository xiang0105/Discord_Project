# message_handler.py
# 處理 /chat 指令、回傳格式、貼圖，以及與 History / Evolution 的串接

import re
import typing as t
import discord
from discord import app_commands
from discord.ext import commands
import asyncio

# from config_manager import ConfigManager
from models.memory_manager import MemoryManager
from models.history_manager import HistoryManager
from models.sticker_manager import StickerManager
from models.utils import smart_split

class MessageHandler:
    def __init__(self, bot: commands.Bot, ai_model, config: dict):
        """
        bot: discord bot instance
        ai_model: 你的 AIModel 實例 (提供 build_system_instruction, start_chat 等)
        config: 由 ConfigManager.load() 取得的設定 dict
        """
        self.bot = bot
        self.ai = ai_model
        self.config = config
        self.evolution_task = None  # 可以在 main.py 建立後注入

    def attach_evolution_task(self, evolution_task):
        """讓外部注入 EvolutionTask 物件（以便 touch_user）"""
        self.evolution_task = evolution_task

    def register_commands(self):
        """註冊 /chat、/reset 等指令與 on_ready 事件"""
        
        @self.bot.event
        async def on_ready():
            # 同步 Slash 指令並列印簡短訊息
            try:
                await self.bot.tree.sync()
                print(f"{self.bot.user} 已上線，/chat 可用")
                
                if self.evolution_task:
                    # 使用 bot 自己的 loop 來建立任務
                    self.bot.loop.create_task(self.evolution_task.run())
                    
            except Exception as e:
                print("同步指令失敗：", e)
                
        @self.bot.event
        async def on_message(message: discord.Message):
            # 1. 忽略 Bot 自己的訊息，避免無線迴圈
            if message.author.bot:
                return

            # 2. 檢查是否在「允許的頻道」
            # (如果 config.json 的 allowed_channels 是空的 []，則預設所有頻道都會回，這可能很吵，建議設定一下)
            allowed = self.config.get("allowed_channels", [])
            if allowed and message.channel.id not in allowed:
                return

            # 3. 觸發輸入中狀態 (顯示 "PhiLia 正在輸入...")
            async with message.channel.typing():
                user_id = str(message.author.id)
                user_message = message.content

                # 若訊息是空的 (例如只有貼圖)，跳過
                if not user_message.strip():
                    return

                # 準備 AI 核心邏輯 (與原本 /chat 相同)
                try:
                    # 1. 【新增】先去撈這個人的記憶
                    user_mem_str = MemoryManager.get_user_memory_str(user_id)
                    
                    if message.mentions:
                        user_mem_str += "\n\n【提及對象的相關記憶】"
                        for mentioned_user in message.mentions:
                            # 忽略機器人自己
                            if mentioned_user.bot:
                                continue
                                
                            m_id = str(mentioned_user.id)
                            m_name = mentioned_user.display_name
                            
                            # 撈記憶
                            mem = MemoryManager.get_user_memory_str(m_id)
                            user_mem_str += f"\n[關於 {m_name} (ID: {m_id})]:\n{mem}"
                    
                    # 2. 【修改】把記憶傳進去 System Instruction
                    system_instr = self.ai.build_system_instruction(self.config, user_memory=user_mem_str)
                    
                    # 3. 呼叫模型
                    model_obj = self.ai.start_chat(system_instruction=system_instr)
                    # ...
                    
                    # 呼叫模型 (採用一問一答模式，不帶入短期歷史給模型，但會存歷史)
                    # 注意：這裡直接生成，不帶 history參數
                    model_obj = self.ai.start_chat(system_instruction=system_instr)
                    resp = await model_obj.generate_content_async(user_message)
                    reply_text = resp.text or ""

                except Exception as e:
                    await message.channel.send(f"(發生錯誤：{e})")
                    return

                # 處理貼圖 tag
                sticker_map = StickerManager.build_sticker_map(message.guild)
                sticker_to_send = None
                match = re.search(r"<STICKER:(.*?)>", reply_text)
                if match:
                    name = match.group(1).strip()
                    if name in sticker_map:
                        sticker_to_send = sticker_map[name]
                    reply_text = reply_text.replace(match.group(0), "").strip()

                # 儲存歷史 (雖然模型這次沒看，但我們存下來供未來演化用)
                try:
                    HistoryManager.append_message(user_id, "user", user_message)
                    HistoryManager.append_message(user_id, "model", reply_text)
                except Exception as e:
                    print("儲存歷史失敗：", e)

                # 回覆訊息 (直接發送，不需要 interaction)
                if reply_text:
                    # 使用 smart_split 切割長訊息
                    for part in smart_split(reply_text, limit=1900):
                        await message.channel.send(part)
                
                # 發送貼圖
                if sticker_to_send:
                    try:
                        await message.channel.send(stickers=[sticker_to_send])
                    except Exception as e:
                        print("貼圖發送失敗：", e)

                # 推進演化任務
                try:
                    if self.evolution_task:
                        frag = f"User: {user_message}\nAI: {reply_text}"
                        self.evolution_task.touch_user(user_id, frag)
                except Exception as e:
                    print("演化任務錯誤：", e)
            
            # 重要：如果有其他指令處理需求，要加上這行 (目前我們只有 slash command 所以還好，但加著保險)
            await self.bot.process_commands(message)

        @self.bot.tree.command(name="chat", description="跟 PhiLia 聊天")
        @app_commands.describe(user_message="你想對 PhiLia 說的話")
        async def chat(interaction: discord.Interaction, user_message: str):
            # 檢查是否允許頻道
            allowed = self.config.get("allowed_channels", [])
            if allowed and interaction.channel_id not in allowed:
                await interaction.response.send_message("此頻道不允許使用 /chat", ephemeral=True)
                return

            # 回應延遲 (避免 3 秒超時)
            await interaction.response.defer()

            user_id = str(interaction.user.id)

            # 準備系統 instruction（人設）
            try:
                system_instr = self.ai.build_system_instruction(self.config)
            except Exception as e:
                await interaction.followup.send(f"建立 system instruction 發生錯誤：{e}")
                return
            
            # 準備貼圖字典（name -> StickerObject）
            sticker_map = StickerManager.build_sticker_map(interaction.guild)

            raw_history = HistoryManager.get_user_history(user_id)
            
            gemini_history = []
            for h in raw_history:
                # 假設 h['parts'] 是一個字串 list
                gemini_history.append({
                    "role": h['role'], # 'user' or 'model'
                    "parts": h['parts']
                })

            # 開始呼叫模型
            try:
                # 1. 取得 model 物件
                model_obj = self.ai.start_chat(system_instruction=system_instr)
                
                # 2. 開啟對話 Session (這裡傳入歷史)
                chat_session = model_obj.start_chat(history=gemini_history)
                
                # 3. 發送訊息 (注意這裡是用 send_message_async，不是 generate_content_async)
                resp = await chat_session.send_message_async(user_message)
                reply_text = resp.text or ""
            except Exception as e:
                await interaction.followup.send(f"呼叫模型失敗：{e}")
                return

            # 處理貼圖 tag（例如 <STICKER:LOL>）
            sticker_to_send = None
            match = re.search(r"<STICKER:(.*?)>", reply_text)
            if match:
                name = match.group(1).strip()
                if name in sticker_map:
                    sticker_to_send = sticker_map[name]
                # 清除 tag
                reply_text = reply_text.replace(match.group(0), "").strip()

            # 儲存歷史
            try:
                HistoryManager.append_message(user_id, "user", user_message)
                HistoryManager.append_message(user_id, "model", reply_text)
            except Exception as e:
                # 儲存失敗不阻礙回覆，但在日誌印出
                print("儲存歷史失敗：", e)

            # 格式化要顯示給 Discord 的內容
            display = reply_text

            # 若過長，用 utils.smart_split 切塊發送
            for part in smart_split(display, limit=1900):
                await interaction.followup.send(part)

            # 若有貼圖，另外再發
            if sticker_to_send:
                try:
                    await interaction.followup.send(stickers=[sticker_to_send])
                except Exception as e:
                    # 貼圖發送失敗不影響主要回覆
                    print("貼圖發送失敗：", e)

            # 推進演化任務（如果已經 attach）
            try:
                if self.evolution_task:
                    # 傳一段簡短的 conversation fragment 給 EvolutionTask
                    frag = f"User: {user_message}\nAI: {reply_text}"
                    self.evolution_task.touch_user(user_id, frag)
            except Exception as e:
                print("推進演化任務發生錯誤：", e)

        @self.bot.tree.command(name="reset", description="清除你的對話歷史")
        async def reset(interaction: discord.Interaction):
            user_id = str(interaction.user.id)
            HistoryManager.clear_user(user_id)
            await interaction.response.send_message("你的歷史已清除。", ephemeral=True)
            
        @self.bot.tree.command(name="force_evolve", description="強制讓 Bot 讀取過往所有對話紀錄並更新記憶")
        async def force_evolve(interaction: discord.Interaction):
            # 1. 權限驗證 (避免被惡意刷錢，建議只允許擁有者或當事人)
            # 這裡設定：只能跑自己的，或者是 Bot 擁有者可以跑別人的
            user_id = str(interaction.user.id)
            
            await interaction.response.defer(ephemeral=True)
            await interaction.followup.send("正在挖掘過去的對話紀錄... 這可能需要一點時間。")

            # 2. 讀取該使用者的所有歷史
            raw_history = HistoryManager.get_user_history(user_id)
            if not raw_history:
                await interaction.followup.send("記憶庫中找不到你的歷史紀錄耶。")
                return

            print(f"[Force Evolve] User {user_id} 共有 {len(raw_history)} 則歷史訊息")

            # 3. 分批處理 (Chunking)
            # 假設每 20 則訊息做一次總結 (避免 Token 爆炸)
            chunk_size = 20
            total_chunks = (len(raw_history) // chunk_size) + 1
            
            processed_count = 0
            
            for i in range(0, len(raw_history), chunk_size):
                # 取出一段 (slice)
                batch = raw_history[i : i + chunk_size]
                
                # 轉成文字格式
                text_block = ""
                for msg in batch:
                    # msg 結構: {'role': 'user'/'model', 'parts': ['...']}
                    role = "User" if msg['role'] == 'user' else "AI"
                    content = msg['parts'][0] if msg['parts'] else ""
                    text_block += f"{role}: {content}\n"
                
                # 4. 呼叫演化任務
                if self.evolution_task:
                    try:
                        # 呼叫原本寫好的 run_evolution
                        await self.evolution_task.run_evolution(user_id, text_block)
                        processed_count += 1
                        print(f"[Force Evolve] 進度: {processed_count}/{total_chunks} 區塊完成")
                        
                        # 休息一下，避免 Google API 覺得你在 DDoS 他 (Rate Limit)
                        await asyncio.sleep(2) 
                        
                    except Exception as e:
                        print(f"[Force Evolve] 區塊失敗: {e}")

            await interaction.followup.send(f"補課完成！我已經重新分析了你的 {len(raw_history)} 則對話紀錄，更新了大腦。")