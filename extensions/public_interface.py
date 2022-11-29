import disnake
from disnake.ext import commands
from typing import Optional
import math
import datetime

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from config import cooldowns, Strings, config
from utils import dt_helpers, dt_report_generators, message_utils
from features.paginator import EmbedView
from database import event_participation_repo, tracking_settings_repo

logger = setup_custom_logger(__name__)

class PublicInterface(Base_Cog):
  def __init__(self, bot):
    super(PublicInterface, self).__init__(bot, __file__)

  @commands.slash_command(name="guild")
  async def guild_commands(self, inter: disnake.CommandInteraction):
    pass

  @guild_commands.sub_command(name="search", description=Strings.event_data_tracker_search_guilds_description)
  @cooldowns.long_cooldown
  async def search_guilds(self, inter: disnake.CommandInteraction,
                          guild_name: Optional[str] = commands.Param(default=None, description="Guild name to search"),
                          sort_by: str = commands.Param(description="Attribute to sort guilds by", choices=["ID", "Level", "Name"]),
                          order: str = commands.Param(description="Order method of attribute", choices=["Ascending", "Descending"])):
    await inter.response.defer(with_message=True, ephemeral=True)

    found_guilds = await dt_helpers.get_guild_info(self.bot, guild_name)
    if found_guilds is None or not found_guilds:
      return await message_utils.generate_error_message(inter, Strings.event_data_tracker_search_guilds_no_guild_found)

    if sort_by == "ID":
      found_guilds.sort(key=lambda x: x[0], reverse=order == "Descending")
    elif sort_by == "Level":
      found_guilds.sort(key=lambda x: x[2], reverse=order == "Descending")
    elif sort_by == "Name":
      found_guilds.sort(key=lambda x: x[1], reverse=order == "Descending")

    number_of_guilds = len(found_guilds)

    num_of_batches = math.ceil(number_of_guilds / 12)
    batches = [found_guilds[i * 12:i * 12 + 12] for i in range(num_of_batches)]

    pages = []
    for batch in batches:
      page = disnake.Embed(title="Guild list", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(page, inter.author)

      for guild in batch:
        guild_id = guild[0]
        guild_name = guild[1]
        guild_level = guild[2]

        page.add_field(name=f"{guild_name}({guild_level})", value=f"ID: {guild_id}")
      pages.append(page)

    embed_view = EmbedView(inter.author, pages, invisible=True)
    await embed_view.run(inter)

  @guild_commands.sub_command(name="report", description=Strings.event_data_tracker_generate_announcements_description)
  @cooldowns.long_cooldown
  async def guild_report(self, inter: disnake.CommandInteraction,
                         guild_id: int = commands.Param(description="Deep Town Guild ID"),
                         detailed: bool = commands.Param(description="Detailed report selector")):
    await inter.response.defer(with_message=True)

    guild_data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
    if guild_data is None:
      return await message_utils.generate_error_message(inter, Strings.event_data_tracker_guild_report_no_data)

    if config.event_data_manager.monitor_all_guilds or guild_id in tracking_settings_repo.get_tracked_guild_ids():
      event_participation_repo.generate_or_update_event_participations(guild_data)

    event_year, event_week = dt_helpers.get_event_index(datetime.datetime.utcnow())
    await dt_report_generators.send_text_guild_report(inter, guild_data, event_year, event_week, detailed)

def setup(bot):
  bot.add_cog(PublicInterface(bot))