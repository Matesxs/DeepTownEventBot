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
from database import event_participation_repo, tracking_settings_repo, dt_user_repo, dt_guild_repo
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

      all_participations = [member_participation.amount for member_participation in member_participations]
      this_year_participations = [p.amount for p in event_participation_repo.get_user_event_participations(dt_user.id, year=current_year)]

      member_front_page = disnake.Embed(title=f"{dt_user.username}", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(member_front_page, inter.author)
      member_front_page.add_field(name="ID", value=str(dt_user.id))
      member_front_page.add_field(name="Level", value=str(dt_user.level))
      member_front_page.add_field(name="Depth", value=str(dt_user.depth))
      member_front_page.add_field(name="Online", value=humanize.naturaltime(current_time - dt_user.last_online) if dt_user.last_online is not None else "Never")
      member_front_page.add_field(name="Current guild", value=f"{member_participations[0].dt_guild.name}({member_participations[0].dt_guild.level})", inline=False)
      member_front_page.add_field(name="Average donate", value=f"{statistics.mean(all_participations):.2f}")
      member_front_page.add_field(name="Median donate", value=f"{statistics.median(all_participations):.2f}", inline=False)
      member_front_page.add_field(name="Average donate last year", value=f"{statistics.mean(this_year_participations):.2f}")
      member_front_page.add_field(name="Median donate last year", value=f"{statistics.median(this_year_participations):.2f}", inline=False)

      member_pages.append(member_front_page)

      participation_pages_data = dt_report_generators.generate_participations_page_strings(member_participations, include_guild=include_all_guilds)
      for participation_page_data in participation_pages_data:
        participation_page = disnake.Embed(title=f"{dt_user.username} event participations", description=f"```py\n{participation_page_data}\n```", color=disnake.Color.dark_blue())
        message_utils.add_author_footer(participation_page, inter.author)
        member_pages.append(participation_page)

      users_embeds.append(member_pages)

    embed_view = EmbedView2D(inter.author, users_embeds, invert_list_dir=True)
    await embed_view.run(inter)

  @guild_commands.sub_command(name="report", description=Strings.public_interface_guild_report_description)
  async def guild_report(self, inter: disnake.CommandInteraction,
                         guild_id: int = commands.Param(description="Deep Town Guild ID")):
    guild_data = await self.grab_guild_data(inter, guild_id)
    if guild_data is None: return

    event_year, event_week = dt_helpers.get_event_index(datetime.datetime.utcnow())
    send_report_function = partial(dt_report_generators.send_text_guild_report, inter, guild_data, event_year, event_week)

    reporter_settings = DataSelector(inter.author, ["No°", "Name", "ID", "Level", "Depth", "Online", "Donate"], ["No°", "Name", "Level", "Donate"], invisible=True)
    await reporter_settings.run(inter)
    await reporter_settings.wait()

    await send_report_function(reporter_settings.get_results())

  @guild_commands.sub_command(name="profile", description=Strings.public_interface_guild_profile_description)
  async def guild_profile(self, inter: disnake.CommandInteraction, guild_name: str=commands.Param(description="Deep Town Guild Name")):
    matched_guilds = dt_guild_repo.get_dt_guilds_by_name(guild_name)
    if not matched_guilds:
      return await message_utils.generate_error_message(inter, Strings.public_interface_guild_profile_no_guilds(guild_name=guild_name))

    guild_profiles = []
    for guild in matched_guilds:
      guild_profile_lists = []

      # If guild is tracked, or we monitor all guild update data and reload guild
      if guild.id in tracking_settings_repo.get_tracked_guild_ids() or config.data_manager.monitor_all_guilds:
        guild_data = await dt_helpers.get_dt_guild_data(self.bot, guild.id)
        if guild_data is not None:
          event_participation_repo.generate_or_update_event_participations(guild_data)
          guild = dt_guild_repo.get_dt_guild(guild.id)

      current_time = datetime.datetime.utcnow()
      current_year, _ = dt_helpers.get_event_index(current_time)

      # Front page
      guild_front_page = disnake.Embed(title=f"{guild.name}", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(guild_front_page, inter.author)
      guild_front_page.add_field(name="ID", value=str(guild.id))
      guild_front_page.add_field(name="Level", value=str(guild.level))
      guild_front_page.add_field(name="Active members", value=str(len(guild.active_members)))
      guild_profile_lists.append(guild_front_page)

      # Members list
      member_data = []
      for member in guild.active_members:
        member_data.append((member.user.id, member.user.username, member.user.level, member.user.depth))

      member_table_strings = tabulate(member_data, ["ID", "Name", "Level", "Depth"], tablefmt="github").split("\n")
      member_page_strings = []
      while member_table_strings:
        data_string, member_table_strings = string_manipulation.add_string_until_length(member_table_strings, 3000, "\n")
        member_page_strings.append(data_string)

      for member_page_string in member_page_strings:
        member_page = disnake.Embed(title=f"{guild.name} members", color=disnake.Color.dark_blue(), description=f"```py\n{member_page_string}\n```")
        message_utils.add_author_footer(guild_front_page, inter.author)
        guild_profile_lists.append(member_page)

      # Event participation stats
      all_guild_participations = event_participation_repo.get_guild_event_participations(guild.id)
      all_guild_participation_amounts = [p[2] for p in all_guild_participations]
      last_year_guild_participations_amounts = [p[2] for p in event_participation_repo.get_guild_event_participations(guild.id, current_year)]

      guild_event_participations_stats_page = disnake.Embed(title=f"{guild.name} event participations stats", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(guild_event_participations_stats_page, inter.author)
      guild_event_participations_stats_page.add_field(name="Average donate per event", value=f"{statistics.mean(all_guild_participation_amounts):.2f}", inline=False)
      guild_event_participations_stats_page.add_field(name="Median donate per event", value=f"{statistics.median(all_guild_participation_amounts):.2f}", inline=False)
      guild_event_participations_stats_page.add_field(name="Average donate per event last year", value=f"{statistics.mean(last_year_guild_participations_amounts):.2f}", inline=False)
      guild_event_participations_stats_page.add_field(name="Median donate per event last year", value=f"{statistics.median(last_year_guild_participations_amounts):.2f}", inline=False)
      guild_profile_lists.append(guild_event_participations_stats_page)

      # Event participations
      event_participations_data = []
      for year, week, total, average in all_guild_participations:
        best_participant, _ = event_participation_repo.get_best_participant(guild.id, year, week)
        event_participations_data.append((year, week, best_participant if best_participant is not None else "Unknown", f"{float(average):.2f}"))

      event_participations_strings = tabulate(event_participations_data, ["Year", "Week", "Top", "Average"], tablefmt="github").split("\n")
      event_participations_page_strings = []
      while event_participations_strings:
        data_string, event_participations_strings = string_manipulation.add_string_until_length(event_participations_strings, 3000, "\n")
        event_participations_page_strings.append(data_string)

      for event_participations_page_string in event_participations_page_strings:
        event_participation_page = disnake.Embed(title=f"{guild.name} event participations", color=disnake.Color.dark_blue(), description=f"```py\n{event_participations_page_string}\n```")
        message_utils.add_author_footer(guild_front_page, inter.author)
        guild_profile_lists.append(event_participation_page)

      guild_profiles.append(guild_profile_lists)

    embed_view = EmbedView2D(inter.author, guild_profiles, invert_list_dir=True)
    await embed_view.run(inter)

  @commands.slash_command(name="user")
  @cooldowns.default_cooldown
  async def user_command(self, inter: disnake.CommandInteraction):
    pass

  @user_command.sub_command(name="profile", description=Strings.public_interface_user_profile_description)
  async def user_profile(self, inter: disnake.CommandInteraction, username:str=commands.Param(description="Deep Town User Name")):
    matched_users = dt_user_repo.get_users_by_username(username)
    if not matched_users:
      return await message_utils.generate_error_message(inter, Strings.public_interface_user_profile_no_users(username=username))

    current_time = datetime.datetime.utcnow()
    current_year, _ = dt_helpers.get_event_index(current_time)

    user_profiles = []
    for user in matched_users:
      user_profile_lists = []

      # If user have some active memberships and that guild is tracked, or we monitor all guilds then pull the latest data and update a user
      if user.active_member is not None and (user.active_member.guild.id in tracking_settings_repo.get_tracked_guild_ids() or config.data_manager.monitor_all_guilds):
        guild_data = await dt_helpers.get_dt_guild_data(self.bot, user.active_member.guild.id)
        if guild_data is not None:
          event_participation_repo.generate_or_update_event_participations(guild_data)
          user = dt_user_repo.get_dt_user(user.id)

      all_participations = event_participation_repo.get_user_event_participations(user.id)
      all_participations_amounts = [p.amount for p in all_participations]
      this_year_participations_amounts = [p.amount for p in event_participation_repo.get_user_event_participations(user.id, year=current_year)]

      user_front_page = disnake.Embed(title=f"{user.username}", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(user_front_page, inter.author)
      user_front_page.add_field(name="ID", value=str(user.id))
      user_front_page.add_field(name="Level", value=str(user.level))
      user_front_page.add_field(name="Depth", value=str(user.depth))
      user_front_page.add_field(name="Online", value=humanize.naturaltime(current_time - user.last_online) if user.last_online is not None else "Never")
      user_front_page.add_field(name="Current guild", value=f"{user.active_member.guild.name}({user.active_member.guild.level})" if user.active_member is not None else "None", inline=False)
      user_profile_lists.append(user_front_page)

      user_buildings_page = disnake.Embed(title=f"{user.username} buildings", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(user_buildings_page, inter.author)
      user_buildings_page.add_field(name="Mines", value=str(user.mines))
      user_buildings_page.add_field(name="Chemical mines", value=str(user.chem_mines))
      user_buildings_page.add_field(name="Oil mines", value=str(user.oil_mines))
      user_buildings_page.add_field(name="Crafters", value=str(user.crafters))
      user_buildings_page.add_field(name="Smelters", value=str(user.smelters))
      user_buildings_page.add_field(name="Jewel stations", value=str(user.jewel_stations))
      user_buildings_page.add_field(name="Chemical stations", value=str(user.chem_stations))
      user_buildings_page.add_field(name="Green houses", value=str(user.green_houses))
      user_profile_lists.append(user_buildings_page)

      user_event_participations_stats_page = disnake.Embed(title=f"{user.username} event participations stats", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(user_event_participations_stats_page, inter.author)
      user_event_participations_stats_page.add_field(name="Average donate", value=f"{statistics.mean(all_participations_amounts):.2f}")
      user_event_participations_stats_page.add_field(name="Median donate", value=f"{statistics.median(all_participations_amounts):.2f}", inline=False)
      user_event_participations_stats_page.add_field(name="Average donate last year", value=f"{statistics.mean(this_year_participations_amounts):.2f}")
      user_event_participations_stats_page.add_field(name="Median donate last year", value=f"{statistics.median(this_year_participations_amounts):.2f}", inline=False)
      user_profile_lists.append(user_event_participations_stats_page)

      participation_pages_data = dt_report_generators.generate_participations_page_strings(all_participations, include_guild=True)
      for participation_page_data in participation_pages_data:
        participation_page = disnake.Embed(title=f"{user.username} event participations", description=f"```py\n{participation_page_data}\n```", color=disnake.Color.dark_blue())
        message_utils.add_author_footer(participation_page, inter.author)
        user_profile_lists.append(participation_page)

      user_profiles.append(user_profile_lists)

    embed_view = EmbedView2D(inter.author, user_profiles, invert_list_dir=True)
    await embed_view.run(inter)

def setup(bot):
  bot.add_cog(PublicInterface(bot))