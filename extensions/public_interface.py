import statistics

import disnake
from disnake.ext import commands
from typing import Optional
import math
import datetime
from functools import partial
import humanize
from tabulate import tabulate

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from config import cooldowns, Strings, config
from utils import dt_helpers, dt_report_generators, message_utils, string_manipulation
from features.views.paginator import EmbedView
from features.views.paginator2d import EmbedView2D
from database import event_participation_repo, tracking_settings_repo
from features.views.data_selector import DataSelector

logger = setup_custom_logger(__name__)

class PublicInterface(Base_Cog):
  def __init__(self, bot):
    super(PublicInterface, self).__init__(bot, __file__)

  async def grab_guild_data(self, inter: disnake.CommandInteraction, guild_id: int) -> Optional[dt_helpers.DTGuildData]:
    guild_data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
    if guild_data is None:
      await message_utils.generate_error_message(inter, Strings.public_interface_guild_data_not_found)
      return None

    if config.data_manager.monitor_all_guilds or guild_id in tracking_settings_repo.get_tracked_guild_ids():
      event_participation_repo.generate_or_update_event_participations(guild_data)

    return guild_data

  @commands.slash_command(name="guild")
  @cooldowns.default_cooldown
  async def guild_commands(self, inter: disnake.CommandInteraction):
    pass

  @guild_commands.sub_command(name="search", description=Strings.public_interface_search_guilds_description)
  async def search_guilds(self, inter: disnake.CommandInteraction,
                          guild_name: Optional[str] = commands.Param(default=None, description="Guild name to search"),
                          sort_by: str = commands.Param(description="Attribute to sort guilds by", choices=["ID", "Level", "Name"]),
                          order: str = commands.Param(description="Order method of attribute", choices=["Ascending", "Descending"])):
    await inter.response.defer(with_message=True, ephemeral=True)

    found_guilds = await dt_helpers.get_guild_info(self.bot, guild_name)
    if found_guilds is None or not found_guilds:
      return await message_utils.generate_error_message(inter, Strings.public_interface_guild_data_not_found)

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

  @guild_commands.sub_command(name="members", description=Strings.public_interface_guild_members_description)
  async def guild_members(self, inter: disnake.CommandInteraction,
                          guild_id: int = commands.Param(description="Deep Town Guild ID"),
                          include_all_guilds: bool=commands.Param(default=True, description="Include previous guilds in event participation history")):
    await inter.response.defer(with_message=True)

    guild_data = await self.grab_guild_data(inter, guild_id)
    if guild_data is None: return

    participations_per_user = []
    for member in guild_data.players:
      if include_all_guilds:
        participations_per_user.append(event_participation_repo.get_user_event_participations(member.id))
      else:
        participations_per_user.append(event_participation_repo.get_user_event_participations(member.id, guild_id))

    current_time = datetime.datetime.utcnow()
    current_year, _ = dt_helpers.get_event_index(current_time)

    users_embeds = []
    for member_participations in participations_per_user:
      member_pages = []
      dt_user = member_participations[0].dt_user

      participation_data = []
      participations = []
      for member_participation in member_participations:
        if include_all_guilds:
          participation_data.append((member_participation.event_year, member_participation.event_week, member_participation.dt_guild.name, member_participation.amount))
        else:
          participation_data.append((member_participation.event_year, member_participation.event_week, member_participation.amount))
        participations.append(member_participation.amount)

      participation_table_lines = tabulate(participation_data, ["Year", "Week", "Donate"] if not include_all_guilds else ["Year", "Week", "Guild", "Donate"], tablefmt="github").split("\n")

      this_year_participations = [p.amount for p in event_participation_repo.get_user_event_participations(dt_user.id, guild_id, current_year)]

      member_front_page = disnake.Embed(title=f"{dt_user.username}", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(member_front_page, inter.author)
      member_front_page.add_field(name="ID", value=str(dt_user.id))
      member_front_page.add_field(name="Level", value=str(dt_user.level))
      member_front_page.add_field(name="Depth", value=str(dt_user.depth))
      member_front_page.add_field(name="Online", value=humanize.naturaltime(current_time - dt_user.last_online) if dt_user.last_online is not None else "Never")
      member_front_page.add_field(name="Current guild", value=f"{member_participations[0].dt_guild.name}({member_participations[0].dt_guild.level})", inline=False)
      member_front_page.add_field(name="Average donate", value=f"{statistics.mean(participations):.2f}")
      member_front_page.add_field(name="Median donate", value=f"{statistics.median(participations):.2f}", inline=False)
      member_front_page.add_field(name="Average donate last year", value=f"{statistics.mean(this_year_participations):.2f}")
      member_front_page.add_field(name="Median donate last year", value=f"{statistics.median(this_year_participations):.2f}", inline=False)

      member_pages.append(member_front_page)

      while participation_table_lines:
        data_string, participation_table_lines = string_manipulation.add_string_until_length(participation_table_lines, 1500, "\n")
        participation_page = disnake.Embed(title=f"{dt_user.username} event participations", description=f"```py\n{data_string}\n```", color=disnake.Color.dark_blue())
        message_utils.add_author_footer(participation_page, inter.author)
        member_pages.append(participation_page)

      users_embeds.append(member_pages)

    embed_view = EmbedView2D(inter.author, users_embeds)
    await embed_view.run(inter)

  @guild_commands.sub_command(name="report", description=Strings.public_interface_guild_report_description)
  async def guild_report(self, inter: disnake.CommandInteraction,
                         guild_id: int = commands.Param(description="Deep Town Guild ID")):
    await inter.response.defer(with_message=True, ephemeral=True)

    guild_data = await self.grab_guild_data(inter, guild_id)
    if guild_data is None: return

    event_year, event_week = dt_helpers.get_event_index(datetime.datetime.utcnow())
    send_report_function = partial(dt_report_generators.send_text_guild_report, inter, guild_data, event_year, event_week)

    reporter_settings = DataSelector(inter.author, ["No°", "Name", "ID", "Level", "Depth", "Online", "Donate"], ["No°", "Name", "Level", "Donate"], invisible=True)
    await reporter_settings.run(inter)
    await reporter_settings.wait()

    await send_report_function(reporter_settings.get_results())

  @commands.slash_command(name="user")
  @cooldowns.default_cooldown
  @commands.is_owner() # TODO: Remove - only because in progress
  async def user_command(self, inter: disnake.CommandInteraction):
    pass

  @user_command.sub_command(name="profile", description="WIP")
  async def user_profile(self, inter: disnake.CommandInteraction, username:str=commands.Param(description="Username of Deep Town user")):
    await inter.response.defer(with_message=True)

def setup(bot):
  bot.add_cog(PublicInterface(bot))