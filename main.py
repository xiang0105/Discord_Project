# import asyncio
import os
import discord
from discord.ext import commands
# from discord import app_commands
from dotenv import load_dotenv

from models.config_manager import ConfigManager
from models.ai_model import AIModel
from models.message_handler import MessageHandler
from models.evolution_task import EvolutionTask

load_dotenv()

if __name__ == '__main__':
    config = ConfigManager.load()

    # Sensitive values must come from environment variables.
    google_api_key = os.getenv('GOOGLE_API_KEY')
    token = os.getenv('DISCORD_TOKEN')
    bot_owner_id = os.getenv('BOT_OWNER_ID')

    if bot_owner_id:
        config['bot_owner_id'] = bot_owner_id

    if not google_api_key:
        print('請在環境變數或 .env 設定 GOOGLE_API_KEY')
        raise SystemExit(1)

    if not token:
        print('請在環境變數或 .env 設定 DISCORD_TOKEN')
        raise SystemExit(1)

    # 建立 AI 模型介面（固定 model）
    ai = AIModel(api_key=google_api_key)
    
    # 顯示可用模型
    # ai.list_models() 
    # print("-" * 30)

    # Bot intents
    intents = discord.Intents.default()
    intents.message_content = True 
    intents.members = True

    bot = commands.Bot(command_prefix='/', intents=intents)

    # 註冊樹狀指令與處理器
    msg_handler = MessageHandler(bot=bot, ai_model=ai, config=config)
    msg_handler.register_commands()

    # 啟動背景演化任務
    evolution = EvolutionTask(bot=bot, ai_model=ai, config=config, message_handler=msg_handler)
    # evolution.start()

    msg_handler.attach_evolution_task(evolution)

    # 啟動 bot
    bot.run(token)