import logging
import os
import sys

import discord
from discord.ext import commands
from dotenv import load_dotenv

from models.ai_model import AIModel
from models.config_manager import ConfigManager
from models.evolution_task import EvolutionTask
from models.message_handler import MessageHandler


def require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        logging.error("Missing required environment variable: %s", name)
        raise SystemExit(1)
    return value


def configure_logging() -> None:
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def main() -> None:
    load_dotenv()
    configure_logging()

    config = ConfigManager.load()
    google_api_key = require_env("GOOGLE_API_KEY")
    token = require_env("DISCORD_TOKEN")

    bot_owner_id = os.getenv("BOT_OWNER_ID", "").strip()
    if bot_owner_id:
        if not bot_owner_id.isdigit():
            logging.error("BOT_OWNER_ID must be a Discord numeric user id.")
            raise SystemExit(1)
        config["bot_owner_id"] = bot_owner_id

    ai = AIModel(api_key=google_api_key)

    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = False

    bot = commands.Bot(command_prefix="/", intents=intents)

    msg_handler = MessageHandler(bot=bot, ai_model=ai, config=config)
    msg_handler.register_commands()

    evolution = EvolutionTask(
        bot=bot,
        ai_model=ai,
        config=config,
        message_handler=msg_handler,
    )
    msg_handler.attach_evolution_task(evolution)

    try:
        bot.run(token)
    except discord.LoginFailure:
        logging.error("Discord login failed. Check DISCORD_TOKEN.")
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        logging.info("Bot stopped by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
