import disnake
from disnake.ext import commands
from typing import Optional
import math

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from utils import dt_helpers, message_utils, permission_helper
from database import event_participation_repo, tracking_settings_repo
from config import Strings, cooldowns
from features.paginator import EmbedView

logger = setup_custom_logger(__name__)

class EventDataCollectorInterface(Base_Cog):
  def __init__(self, bot):
    super(EventDataCollectorInterface, self).__init__(bot, __file__)

  @commands.slash_command()
  async def tracker_settings(self, inter: disnake.CommandInteraction):
    pass

  @tracker_settings.sub_command(description=Strings.event_data_collector_settings_add_or_modify_tracker_description)
  @commands.check(permission_helper.is_administrator)
  @cooldowns.default_cooldown
  @commands.guild_only()
  async def add_or_modify_tracker(self, inter: disnake.CommandInteraction,
                                  guild_id: int=commands.Param(description="Deep Town Guild ID"),
                                  announce_channel:Optional[disnake.TextChannel]=commands.Param(default=None, description="Channel for announcing results at the end of event")):
    await inter.response.defer(with_message=True, ephemeral=True)

    data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
    if data is None:
      return await message_utils.generate_error_message(inter, Strings.event_data_collector_settings_add_or_modify_tracker_failed_to_get_data)

    event_participation_repo.generate_or_update_event_participations(data)
    tracking_settings_repo.get_or_create_tracking_settings(inter.guild, data, announce_channel.id if announce_channel is not None else None)

    if announce_channel is None:
      await message_utils.generate_success_message(inter, Strings.event_data_collector_settings_add_or_modify_tracker_success_without_channel(guild=data.name))
    else:
      await message_utils.generate_success_message(inter, Strings.event_data_collector_settings_add_or_modify_tracker_success_with_channel(guild=data.name, channel=announce_channel.name))

  @tracker_settings.sub_command(description=Strings.event_data_collector_settings_remove_tracker_description)
  @commands.check(permission_helper.is_administrator)
  @cooldowns.default_cooldown
  @commands.guild_only()
  async def remove_tracker(self, inter: disnake.CommandInteraction,
                                 guild_id: int=commands.Param(description="Deep Town Guild ID")):
    await inter.response.defer(with_message=True, ephemeral=True)

    settings = tracking_settings_repo.get_tracking_settings(inter.guild.id, guild_id)
    guild_name = settings.dt_guild.name

    if tracking_settings_repo.remove_tracking_settings(inter.guild.id, guild_id):
      await message_utils.generate_success_message(inter, Strings.event_data_collector_settings_remove_tracker_success(guild=guild_name))
    else:
      await message_utils.generate_error_message(inter, Strings.event_data_collector_settings_remove_tracker_failed(guild_id=guild_id))

  @tracker_settings.sub_command(description=Strings.event_data_collector_settings_list_trackers_description)
  @commands.check(permission_helper.is_administrator)
  @cooldowns.default_cooldown
  @commands.guild_only()
  async def list_guild_trackers(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    guild_trackers = tracking_settings_repo.get_all_guild_trackers(inter.guild.id)
    number_of_trackers = len(guild_trackers)

    if number_of_trackers == 0:
      return await message_utils.generate_error_message(inter, Strings.event_data_collector_settings_list_trackers_no_trackers)

    num_of_batches = math.ceil(number_of_trackers / 12)
    batches = [guild_trackers[i * 12:i * 12 + 12] for i in range(num_of_batches)]

    pages = []
    for batch in batches:
      page = disnake.Embed(title="Tracker list", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(page, inter.author)

      for setting in batch:
        guild_name = setting.dt_guild.name
        guild_level = setting.dt_guild.level
        announce_channel = await setting.get_announce_channel(self.bot)

        page.add_field(name=f"{guild_name}({guild_level})", value="No reporting" if announce_channel is None else announce_channel.name)
      pages.append(page)

    embed_view = EmbedView(inter.author, pages, invisible=True)
    await embed_view.run(inter)

def setup(bot):
  bot.add_cog(EventDataCollectorInterface(bot))
