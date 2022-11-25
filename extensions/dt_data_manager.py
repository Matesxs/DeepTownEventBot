import disnake
from disnake.ext import commands, tasks
import asyncio

from features.base_cog import Base_Cog
from utils import dt_helpers, message_utils
from utils.logger import setup_custom_logger
from config import cooldowns, Strings, config
from database import event_participation_repo, tracking_settings_repo, dt_guild_repo

logger = setup_custom_logger(__name__)

class DTDataManager(Base_Cog):
  def __init__(self, bot):
    super(DTDataManager, self).__init__(bot, __file__)
    if not self.cleanup_task.is_running():
      self.cleanup_task.start()

  def cog_unload(self):
    if self.cleanup_task.is_running():
      self.cleanup_task.cancel()

  @commands.slash_command()
  @commands.is_owner()
  async def manager(self, inter: disnake.CommandInteraction):
    pass

  @manager.sub_command(description=Strings.event_data_manager_update_guild_data_description)
  @cooldowns.long_cooldown
  async def update_guild(self, inter: disnake.CommandInteraction, guild_id: int=commands.Param(description="Deep Town Guild ID")):
    await inter.response.defer(with_message=True, ephemeral=True)

    data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
    if data is None:
      return await message_utils.generate_error_message(inter, Strings.event_data_manager_update_guild_data_get_failed)

    event_participation_repo.generate_or_update_event_participations(data)

    await message_utils.generate_success_message(inter, Strings.event_data_manager_update_guild_data_success(guild=data.name))

  @manager.sub_command(description=Strings.event_data_manager_update_all_guilds_data_description)
  @cooldowns.long_cooldown
  async def update_all_guilds(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    guild_ids = await dt_helpers.get_ids_of_all_guilds(self.bot)

    if guild_ids is not None or not guild_ids:
      pulled_data = 0

      for guild_id in guild_ids:
        data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
        if data is None: continue

        event_participation_repo.generate_or_update_event_participations(data)
        pulled_data += 1
        await asyncio.sleep(1)

      return await message_utils.generate_success_message(inter, Strings.event_data_manager_update_all_guilds_data_success(guild_num=pulled_data))
    await message_utils.generate_error_message(inter, Strings.event_data_manager_update_all_guilds_data_failed)

  @manager.sub_command(description=Strings.event_data_manager_update_data_description)
  @cooldowns.long_cooldown
  async def update_tracked_guilds(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    if not config.event_data_manager.monitor_all_guilds:
      guild_ids = tracking_settings_repo.get_tracked_guild_ids()
    else:
      guild_ids = await dt_helpers.get_ids_of_all_guilds(self.bot)

    if guild_ids is not None or not guild_ids:
      pulled_data = 0

      for guild_id in guild_ids:
        data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
        if data is None: continue

        event_participation_repo.generate_or_update_event_participations(data)
        pulled_data += 1
        await asyncio.sleep(1)

      return await message_utils.generate_success_message(inter, Strings.event_data_manager_update_data_success(guild_num=pulled_data))
    await message_utils.generate_error_message(inter, Strings.event_data_manager_update_data_failed)

  @tasks.loop(hours=config.event_data_manager.cleanup_rate_days * 24)
  async def cleanup_task(self):
    logger.info("Starting cleanup")
    all_guild_ids = await dt_helpers.get_ids_of_all_guilds(self.bot)
    if all_guild_ids is None:
      logger.error("Failed to get all ids of guilds")
    else:
      removed_guilds = dt_guild_repo.remove_deleted_guilds(all_guild_ids)
      logger.info(f"Remove {removed_guilds} deleted guilds from database")
    logger.info("Cleanup finished")

def setup(bot):
  bot.add_cog(DTDataManager(bot))
