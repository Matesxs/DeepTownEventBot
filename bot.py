import disnake

from features.base_bot import BaseAutoshardedBot
from config import config
from utils.logger import setup_custom_logger
from database import init_tables

logger = setup_custom_logger(__name__)

if config.base.discord_api_key is None:
  logger.error("Discord API key is missing!")
  exit(-1)

intents = disnake.Intents.none()
intents.guilds = True
intents.members = True
intents.emojis = True
intents.messages = True
intents.message_content = True
intents.reactions = True

if __name__ == '__main__':
  init_tables()
  bot = BaseAutoshardedBot(config.base.command_prefix, intents, "core_extensions", "extensions", config.base.default_loaded_extensions)
  bot.run(config.base.discord_api_key)
