import disnake
from disnake.ext import commands, tasks

from features.base_cog import Base_Cog
from utils import dt_helpers, message_utils
from utils.logger import setup_custom_logger
from config import cooldowns, Strings, config
from database import event_participation_repo, tracking_settings_repo

logger = setup_custom_logger(__name__)

class EventDataCollector(Base_Cog):
  def __init__(self, bot):
    super(EventDataCollector, self).__init__(bot, __file__)
    if not self.update_data_task.is_running():
      self.update_data_task.start()

  def cog_unload(self):
    if self.update_data_task.is_running():
      self.update_data_task.cancel()

  @commands.slash_command()
  @commands.is_owner()
  async def data_collector(self, inter: disnake.CommandInteraction):
    pass

  @data_collector.sub_command(description=Strings.event_data_collector_fetch_data_description)
  @cooldowns.default_cooldown
  async def fetch_guild_data(self, inter: disnake.CommandInteraction, guild_id: int=commands.Param(description="Deep Town Guild ID")):
    await inter.response.defer(with_message=True, ephemeral=True)

    data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
    if data is None:
      return await message_utils.generate_error_message(inter, Strings.event_data_collector_fetch_data_get_failed)

    event_participation_repo.generate_or_update_event_participations(data)

    await message_utils.generate_success_message(inter, Strings.event_data_collector_fetch_data_success(guild=data.name))

  @tasks.loop(hours=config.event_data_collector.pull_rate_hours)
  async def update_data_task(self):
    logger.info("Starting pulling")
    guild_ids = tracking_settings_repo.get_tracked_guild_ids()
    for guild_id in guild_ids:
      data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
      event_participation_repo.generate_or_update_event_participations(data)
    logger.info("Pulling done")

def setup(bot):
  bot.add_cog(EventDataCollector(bot))
