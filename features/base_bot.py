# Precursor for bot class

import datetime
import disnake
from disnake.ext import commands
import traceback

from utils import message_utils, object_getters, command_utils
from config import config
from utils.logger import setup_custom_logger
from features.presence_handler import PresenceHandler
from features.error_logger import ErrorLogger

logger = setup_custom_logger(__name__)

class BaseAutoshardedBot(commands.AutoShardedBot):
  def __init__(self, prefix, intents, core_extensions_folder, extensions_folder, default_extensions):
    super(BaseAutoshardedBot, self).__init__(
      command_prefix=commands.when_mentioned_or(prefix),
      help_command=None,
      case_insensitive=True,
      allowed_mentions=disnake.AllowedMentions(roles=False, everyone=False, users=True),
      intents=intents,
      command_sync_flags=commands.CommandSyncFlags.all() if config.base.command_sync_debug else commands.CommandSyncFlags.default()
    )
    self.initialized = False

    self.last_error = None
    self.start_time = datetime.datetime.utcnow()

    self.core_extensions_folder = core_extensions_folder
    self.extensions_folder = extensions_folder

    self.presence_handler = PresenceHandler(self, config.presence.status_messages, config.presence.cycle_interval_s)
    self.error_logger = ErrorLogger(self)

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

    self.presence_handler.start()

  async def on_ready(self):
    if self.initialized: return
    self.initialized = True

    logger.info(f"Logged in as: {self.user} (ID: {self.user.id}) on {self.shard_count} shards in {len(self.guilds)} guilds serving {len(self.users)} users")
    logger.info(f"Invite link: https://discord.com/oauth2/authorize?client_id={self.user.id}&scope=bot&permissions={config.base.required_permissions}")
    log_channel = await object_getters.get_or_fetch_channel(self, config.base.log_channel_id)
    if log_channel is not None:
      await message_utils.generate_success_message(log_channel, "Bot is ready!")
    logger.info("Ready!")

  async def on_connect(self):
    logger.info("Bot connected to discord")
    if self.initialized:
      await self.presence_handler.update_message()

  async def on_error(self, event, *args, **kwargs):
    return await self.error_logger.default_error_handling(event, args, kwargs)
