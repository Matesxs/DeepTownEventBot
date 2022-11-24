import disnake
from disnake.ext import commands, tasks
import asyncio

from features.base_cog import Base_Cog
from utils import dt_helpers, message_utils
from utils.logger import setup_custom_logger
from config import cooldowns, Strings, config
from database import event_participation_repo, tracking_settings_repo, dt_guild_repo

logger = setup_custom_logger(__name__)

class EventDataCollector(Base_Cog):
  def __init__(self, bot):
    super(EventDataCollector, self).__init__(bot, __file__)
    if not self.cleanup_task.is_running():
      self.cleanup_task.start()

    if not self.update_data_task.is_running():
      self.update_data_task.start()

  def cog_unload(self):
    if self.cleanup_task.is_running():
      self.cleanup_task.cancel()

    if self.update_data_task.is_running():
      self.update_data_task.cancel()

  @commands.slash_command()
  @commands.is_owner()
  async def collector(self, inter: disnake.CommandInteraction):
    pass

  @collector.sub_command(description=Strings.event_data_collector_fetch_data_description)
  @cooldowns.default_cooldown
  async def fetch_guild_data(self, inter: disnake.CommandInteraction, guild_id: int=commands.Param(description="Deep Town Guild ID")):
    await inter.response.defer(with_message=True, ephemeral=True)

    data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
    if data is None:
      return await message_utils.generate_error_message(inter, Strings.event_data_collector_fetch_data_get_failed)

    event_participation_repo.generate_or_update_event_participations(data)

    await message_utils.generate_success_message(inter, Strings.event_data_collector_fetch_data_success(guild=data.name))

  @collector.sub_command(description=Strings.event_data_collector_update_data_description)
  @cooldowns.default_cooldown
  async def update_data(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    guild_ids = tracking_settings_repo.get_tracked_guild_ids()
    for guild_id in guild_ids:
      data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
      event_participation_repo.generate_or_update_event_participations(data)
      await asyncio.sleep(0.5)

    await message_utils.generate_success_message(inter, Strings.event_data_collector_update_data_success(guild_num=len(guild_ids)))

  @tasks.loop(hours=config.event_data_collector.cleanup_rate_days * 24)
  async def cleanup_task(self):
    logger.info("Starting cleanup")
    all_guild_ids = await dt_helpers.get_ids_of_all_guilds(self.bot)
    if all_guild_ids is None:
      logger.error("Failed to get all ids of guilds")
    else:
      removed_guilds = dt_guild_repo.remove_deleted_guilds(all_guild_ids)
      logger.info(f"Remove {removed_guilds} deleted guilds from database")
    logger.info("Cleanup finished")

  @tasks.loop(hours=config.event_data_collector.pull_rate_hours)
  async def update_data_task(self):
    await asyncio.sleep(10)

    logger.info("Starting pulling")
    if not config.event_data_collector.monitor_all_guilds:
      guild_ids = tracking_settings_repo.get_tracked_guild_ids()
    else:
      guild_ids = await dt_helpers.get_ids_of_all_guilds(self.bot)

    if guild_ids is not None:
      for guild_id in guild_ids:
        data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
        if data is None: continue

        event_participation_repo.generate_or_update_event_participations(data)
        await asyncio.sleep(1)
    else:
      logger.error("Failed to pull guild ids")
    logger.info("Pulling finished")

def setup(bot):
  bot.add_cog(EventDataCollector(bot))
