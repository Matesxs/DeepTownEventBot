import disnake
from disnake.ext import tasks
import asyncio
import datetime

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from config import config
from utils import dt_helpers
from database import dt_guild_repo, event_participation_repo, dt_blacklist_repo
from database.tables import dt_statistics

logger = setup_custom_logger(__name__)

class DTDataDownloader(Base_Cog):
  def __init__(self, bot):
    super(DTDataDownloader, self).__init__(bot, __file__)

  def cog_load(self):
    if config.data_manager.clean_none_existing_guilds:
      if not self.cleanup_task.is_running():
        self.cleanup_task.start()

    if config.data_manager.periodically_pull_data:
      if not self.data_update_task.is_running():
        self.data_update_task.start()

  def cog_unload(self):
    if self.cleanup_task.is_running():
      self.cleanup_task.cancel()

    if self.data_update_task.is_running():
      self.data_update_task.cancel()

    if self.inactive_guild_data_update_task.is_running():
      self.inactive_guild_data_update_task.cancel()

  @tasks.loop(hours=config.data_manager.cleanup_rate_days * 24)
  async def cleanup_task(self):
    logger.info("Starting cleanup")
    all_guild_ids = await dt_helpers.get_ids_of_all_guilds()
    if all_guild_ids is None:
      logger.error("Failed to get all ids of guilds")
    else:
      removed_guilds = await dt_guild_repo.remove_deleted_guilds(all_guild_ids)
      logger.info(f"Remove {removed_guilds} deleted guilds from database")
    logger.info("Cleanup finished")

  @tasks.loop(hours=config.data_manager.inactive_guild_data_pull_rate_hours)
  async def inactive_guild_data_update_task(self):
    inactive_guild_ids = await dt_guild_repo.get_inactive_guild_ids()

    logger.info("Inactive DT Guild data pull starting")

    if inactive_guild_ids:
      pulled_data = 0

      for idx, guild_id in enumerate(inactive_guild_ids):
        data = await dt_helpers.get_dt_guild_data(guild_id)

        await asyncio.sleep(2)
        if data is None:
          continue

        await event_participation_repo.generate_or_update_event_participations(data)
        pulled_data += 1

      logger.info(f"Pulled data of {pulled_data} inactive DT guilds")
      logger.info(f"New count of active guilds: {await dt_guild_repo.get_number_of_active_guilds()}")

      # Generate new activity statistics
      await dt_statistics.DTActiveEntitiesData.generate()
    logger.info("Inactive DT Guild data pull finished")

  @tasks.loop(hours=max(config.data_manager.data_pull_rate_hours, 1))
  async def data_update_task(self):
    await asyncio.sleep(config.data_manager.pull_data_startup_delay_seconds)

    logger.info("DT Guild data pull starting")
    guild_ids = await dt_helpers.get_ids_of_all_guilds()
    await asyncio.sleep(0.1)

    if guild_ids is not None and guild_ids:
      pulled_data = 0
      not_updated = []

      self.bot.presence_handler.stop()

      last_update = datetime.datetime.utcnow()
      await self.bot.change_presence(activity=disnake.Game(name="Updating data..."), status=disnake.Status.dnd)

      number_of_guilds = len(guild_ids)
      for idx, guild_id in enumerate(guild_ids):
        if datetime.datetime.utcnow() - last_update >= datetime.timedelta(minutes=1):
          progress_percent = (idx / number_of_guilds) * 100
          await self.bot.change_presence(activity=disnake.Game(name=f"Updating data {progress_percent:.1f}%..."), status=disnake.Status.dnd)
          last_update = datetime.datetime.utcnow()

        if (await dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.GUILD, guild_id)) or not (await dt_guild_repo.is_guild_active(guild_id)):
          continue

        data = await dt_helpers.get_dt_guild_data(guild_id)

        await asyncio.sleep(1)
        if data is None:
          not_updated.append(guild_id)
          continue

        await event_participation_repo.generate_or_update_event_participations(data)
        pulled_data += 1

      number_of_not_updated_guilds = len(not_updated)
      if number_of_not_updated_guilds > 0:
        logger.info(f"{number_of_not_updated_guilds} guild not updated, retrying")

        await asyncio.sleep(30)

        last_update = datetime.datetime.utcnow()
        await self.bot.change_presence(activity=disnake.Game(name="Updating data..."), status=disnake.Status.dnd)

        for idx, guild_id in enumerate(not_updated.copy()):
          if datetime.datetime.utcnow() - last_update >= datetime.timedelta(minutes=1):
            progress_percent = (idx / number_of_not_updated_guilds) * 100
            await self.bot.change_presence(activity=disnake.Game(name=f"Updating data {progress_percent:.1f}%..."), status=disnake.Status.dnd)
            last_update = datetime.datetime.utcnow()

          if (await dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.GUILD, guild_id)) or not (await dt_guild_repo.is_guild_active(guild_id)):
            continue

          data = await dt_helpers.get_dt_guild_data(guild_id)

          await asyncio.sleep(1)
          if data is None:
            continue

          not_updated.remove(guild_id)
          await event_participation_repo.generate_or_update_event_participations(data)
          pulled_data += 1

      logger.info(f"Pulled data of {pulled_data} DT guilds\n{not_updated} guilds not updated")

      # Generate new activity statistics
      await dt_statistics.DTActiveEntitiesData.generate()

    logger.info("DT Guild data pull finished")

    await asyncio.sleep(30)
    self.bot.presence_handler.start()

    if not self.inactive_guild_data_update_task.is_running() and config.data_manager.inactive_guild_data_pull_rate_hours > 0:
      self.inactive_guild_data_update_task.start()

def setup(bot):
  bot.add_cog(DTDataDownloader(bot))
