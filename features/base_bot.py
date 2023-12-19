# Precursor for bot class

import datetime
import disnake
from disnake.ext import commands
import traceback

from utils import message_utils, object_getters, command_utils
from config import config
from utils.logger import setup_custom_logger

logger = setup_custom_logger(__name__)

class BaseAutoshardedBot(commands.AutoShardedBot):
  def __init__(self, prefix, intents, core_extensions_folder, extensions_folder, default_extensions):
    super(BaseAutoshardedBot, self).__init__(
      command_prefix=commands.when_mentioned_or(prefix),
      help_command=None,
      case_insensitive=True,
      allowed_mentions=disnake.AllowedMentions(roles=False, everyone=False, users=True),
      intents=intents,
      sync_commands=True,
      sync_commands_on_cog_unload=True
    )
    self.initialized = False

    self.last_error = None
    self.start_time = datetime.datetime.utcnow()

    self.core_extensions_folder = core_extensions_folder
    self.extensions_folder = extensions_folder

    self.event(self.on_ready)

    for cog in command_utils.get_cogs_in_folder(self.core_extensions_folder):
      try:
        self.load_extension(f"{self.core_extensions_folder}.{cog}")
        logger.info(f"{cog} loaded")
      except commands.ExtensionNotFound:
        logger.warning(f"Failed to load {cog} module - Not found")
      except:
        output = traceback.format_exc()
        logger.error(f"Failed to load {cog} module\n{output}")
        exit(-2)
    logger.info("Protected modules loaded")

    for cog in default_extensions:
      try:
        self.load_extension(f"{self.extensions_folder}.{cog}")
        logger.info(f"{cog} loaded")
      except commands.ExtensionNotFound:
        logger.warning(f"Failed to load {cog} module - Not found")
      except:
        output = traceback.format_exc()
        logger.warning(f"Failed to load {cog} module\n{output}")
    logger.info("Defaul modules loaded")

  async def on_ready(self):
    await self.change_presence(activity=disnake.Game(name=config.base.status_message, type=0), status=disnake.Status.online)

    if self.initialized: return
    self.initialized = True

    logger.info(f"Logged in as: {self.user} (ID: {self.user.id}) on {self.shard_count} shards in {len(self.guilds)} guilds")
    logger.info(f"Invite link: https://discord.com/oauth2/authorize?client_id={self.user.id}&scope=bot&permissions={config.base.required_permissions}")
    log_channel = await object_getters.get_or_fetch_channel(self, config.base.log_channel_id)
    if log_channel is not None:
      await message_utils.generate_success_message(log_channel, "Bot is ready!")
    logger.info("Ready!")
