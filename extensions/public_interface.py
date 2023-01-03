import statistics
import disnake
from disnake.ext import commands
from typing import Optional, Union, List
import math
import datetime
from functools import partial
import humanize
from table2ascii import table2ascii, Alignment

from features.base_cog import Base_Cog
from features.base_bot import BaseAutoshardedBot
from utils.logger import setup_custom_logger
from config import cooldowns, Strings
from utils import dt_helpers, dt_report_generators, message_utils, string_manipulation
from features.views.paginator import EmbedView
from features.views.paginator2d import EmbedView2D
from database import event_participation_repo, dt_user_repo, dt_guild_repo, dt_guild_member_repo
from features.views.data_selector import DataSelector

logger = setup_custom_logger(__name__)

async def grab_recent_guild_event_participations(bot: BaseAutoshardedBot, inter: disnake.CommandInteraction, identifier: Union[int, str]) -> Optional[List[event_participation_repo.EventParticipation]]:
  if isinstance(identifier, str):
    guilds = dt_guild_repo.get_dt_guilds_by_identifier(identifier)
    if guilds:
      guild_data = event_participation_repo.get_recent_guild_event_participations(guilds[0].id)

      if not guild_data:
        await message_utils.generate_error_message(inter, Strings.public_interface_guild_data_not_found(identifier=identifier))
        return None
    else:
      # Try to find identifier in guild names on server
      server_guilds = await dt_helpers.get_guild_info(bot, identifier)
      if server_guilds is None or not server_guilds:
        await message_utils.generate_error_message(inter, Strings.public_interface_guild_data_not_found(identifier=identifier))
        return None

      # Try to retrieve data for first matched guild
      guild_data = event_participation_repo.get_recent_guild_event_participations(server_guilds[0][0])

      if not guild_data:
        await message_utils.generate_error_message(inter, Strings.public_interface_guild_data_not_found(identifier=identifier))
        return None
  else:
    guild_data = event_participation_repo.get_recent_guild_event_participations(identifier)

    if not guild_data:
      await message_utils.generate_error_message(inter, Strings.public_interface_guild_data_not_found(identifier=identifier))
      return None

  return guild_data

async def send_event_leaderboards(inter: disnake.CommandInteraction, year: int, week: int, limit: int):
  global_best_participants = event_participation_repo.get_best_participants(year=year, week=week, limit=limit)

  participant_data = [(idx + 1, string_manipulation.truncate_string(username, 20), string_manipulation.truncate_string(guild_name, 20), string_manipulation.format_number(total_contribution)) for idx, (_, username, _, guild_name, total_contribution, _, _) in enumerate(global_best_participants)]
  participant_data_table_strings = (f"Year: {year} Week: {week}\n" + table2ascii(header=["No°", "Username", "Guild", "Donate"], body=participant_data, first_col_heading=True, alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.LEFT, Alignment.RIGHT])).split("\n")

  participant_data_page_strings = []
  while participant_data_table_strings:
    data_string, participant_data_table_strings = string_manipulation.add_string_until_length(participant_data_table_strings, 1900, "\n")
    participant_data_page_strings.append(f"```\n{data_string}\n```")

  for participant_data_page_string in participant_data_page_strings:
    await inter.send(participant_data_page_string)

class PublicInterface(Base_Cog):
  def __init__(self, bot):
    super(PublicInterface, self).__init__(bot, __file__)

  @commands.slash_command(name="guild")
  async def guild_commands(self, inter: disnake.CommandInteraction):
    pass

  @guild_commands.sub_command(name="search", description=Strings.public_interface_search_guilds_description)
  @cooldowns.default_cooldown
  async def search_guilds(self, inter: disnake.CommandInteraction,
                          guild_name: Optional[str] = commands.Param(default=None, description=Strings.public_interface_search_guilds_guild_name_param_description),
                          sort_by: str = commands.Param(description=Strings.public_interface_search_guilds_sort_by_param_description, choices=["ID", "Level", "Name"]),
                          order_mode: str = commands.Param(description=Strings.public_interface_search_guilds_order_mode_param_description, choices=["Ascending", "Descending"])):
    await inter.response.defer(with_message=True)

    found_guilds = await dt_helpers.get_guild_info(self.bot, guild_name)
    if found_guilds is None or not found_guilds:
      return await message_utils.generate_error_message(inter, Strings.public_interface_guild_data_not_received(identifier=guild_name))

    if sort_by == "ID":
      found_guilds.sort(key=lambda x: x[0], reverse=order_mode == "Descending")
    elif sort_by == "Level":
      found_guilds.sort(key=lambda x: x[2], reverse=order_mode == "Descending")
    elif sort_by == "Name":
      found_guilds.sort(key=lambda x: x[1], reverse=order_mode == "Descending")

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

        page.add_field(name=f"{string_manipulation.truncate_string(guild_name, 20)}({guild_level})", value=f"ID: {guild_id}")
      pages.append(page)

    embed_view = EmbedView(inter.author, pages, invisible=True)
    await embed_view.run(inter)

  @guild_commands.sub_command(name="members", description=Strings.public_interface_guild_members_description)
  @cooldowns.default_cooldown
  async def guild_members(self, inter: disnake.CommandInteraction,
                          identifier: str = commands.Param(description=Strings.dt_guild_identifier_param_description)):
    await inter.response.defer(with_message=True)

    guilds = dt_guild_repo.get_dt_guilds_by_identifier(identifier)

    if not guilds:
      await message_utils.generate_error_message(inter, Strings.public_interface_guild_data_not_found(identifier=identifier))
      return None

    guild = guilds[0]

    participations_per_user = []
    for member in guild.active_members:
      participations_per_user.append(event_participation_repo.get_event_participations(user_id=member.dt_user_id))

    current_time = datetime.datetime.utcnow()
    current_year, _ = dt_helpers.get_event_index(current_time)

    users_embeds = []
    for member_participations in participations_per_user:
      member_pages = []
      dt_user = member_participations[0].dt_user

      all_participation_amounts = [member_participation.amount for member_participation in member_participations]
      if not all_participation_amounts: all_participation_amounts = [0]
      this_year_participation_amounts = [p.amount for p in event_participation_repo.get_event_participations(user_id=dt_user.id, year=current_year)]
      if not this_year_participation_amounts: this_year_participation_amounts = [0]

      member_front_page = disnake.Embed(title=f"{string_manipulation.truncate_string(dt_user.username, 20)}", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(member_front_page, inter.author)
      member_front_page.add_field(name="ID", value=str(dt_user.id))
      member_front_page.add_field(name="Level", value=str(dt_user.level))
      member_front_page.add_field(name="Depth", value=str(dt_user.depth))
      member_front_page.add_field(name="Online", value=humanize.naturaltime(current_time - dt_user.last_online) if dt_user.last_online is not None else "Never")
      member_front_page.add_field(name="Current guild", value=f"{member_participations[0].dt_guild.name}({member_participations[0].dt_guild.level})", inline=False)
      member_pages.append(member_front_page)

      member_participation_stats_page = disnake.Embed(title=f"{string_manipulation.truncate_string(dt_user.username, 20)} event participations stats", color=disnake.Color.dark_blue())
      member_participation_stats_page.add_field(name="Average donate", value=f"{string_manipulation.format_number(statistics.mean(all_participation_amounts), 1)}")
      member_participation_stats_page.add_field(name="Median donate", value=f"{string_manipulation.format_number(statistics.median([p for p in all_participation_amounts if p > 0]), 1)}", inline=False)
      member_participation_stats_page.add_field(name="Average donate last year", value=f"{string_manipulation.format_number(statistics.mean(this_year_participation_amounts), 1)}")
      member_participation_stats_page.add_field(name="Median donate last year", value=f"{string_manipulation.format_number(statistics.median([p for p in this_year_participation_amounts if p > 0]), 1)}", inline=False)
      member_pages.append(member_participation_stats_page)

      participation_pages_data = dt_report_generators.generate_participations_page_strings(member_participations)
      for participation_page_data in participation_pages_data:
        participation_page = disnake.Embed(title=f"{string_manipulation.truncate_string(dt_user.username, 20)} event participations", description=f"```\n{participation_page_data}\n```", color=disnake.Color.dark_blue())
        message_utils.add_author_footer(participation_page, inter.author)
        member_pages.append(participation_page)

      users_embeds.append(member_pages)

    embed_view = EmbedView2D(inter.author, users_embeds, invert_list_dir=True)
    await embed_view.run(inter)

  @guild_commands.sub_command(name="report", description=Strings.public_interface_guild_report_description)
  @cooldowns.default_cooldown
  async def guild_report(self, inter: disnake.CommandInteraction,
                         identifier: str = commands.Param(description=Strings.dt_guild_identifier_param_description),
                         tight_format: bool = commands.Param(default=False, description=Strings.public_interface_guild_report_tight_format_param_description)):
    await inter.response.defer(with_message=True)

    guild_data = await grab_recent_guild_event_participations(self.bot, inter, int(identifier) if identifier.isnumeric() else identifier)
    if guild_data is None: return

    send_report_function = partial(dt_report_generators.send_text_guild_event_participation_report, inter, guild_data[0].dt_guild, guild_data, colm_padding=0 if tight_format else 1)

    reporter_settings = DataSelector(inter.author, ["No°", "Name", "ID", "Level", "Depth", "Online", "Donate", "Standing"], ["No°", "Name", "Level", "Donate"], invisible=True)
    await reporter_settings.run(inter)
    ret = await reporter_settings.wait()

    if not ret:
      await send_report_function(reporter_settings.get_results())

  @guild_commands.sub_command(name="profile", description=Strings.public_interface_guild_profile_description)
  @cooldowns.default_cooldown
  async def guild_profile(self, inter: disnake.CommandInteraction, identifier: str = commands.Param(description=Strings.dt_guild_identifier_param_description)):
    await inter.response.defer(with_message=True)

    guilds = dt_guild_repo.get_dt_guilds_by_identifier(identifier)

    if not guilds:
      await message_utils.generate_error_message(inter, Strings.public_interface_guild_data_not_found(identifier=identifier))
      return None

    guild_profiles = []
    for guild in guilds:
      guild_profile_lists = []

      guild_data = await dt_helpers.get_dt_guild_data(self.bot, guild.id)
      if guild_data is not None:
        event_participation_repo.generate_or_update_event_participations(guild_data)
        guild = dt_guild_repo.get_dt_guild(guild.id)

      current_time = datetime.datetime.utcnow()
      current_year, _ = dt_helpers.get_event_index(current_time)

      # Front page
      guild_front_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 20)}", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(guild_front_page, inter.author)
      guild_front_page.add_field(name="ID", value=str(guild.id))
      guild_front_page.add_field(name="Level", value=str(guild.level))
      guild_front_page.add_field(name="Members", value=str(len(guild.active_members)))
      guild_front_page.add_field(name="Position", value=str(dt_guild_repo.get_guild_level_leaderboard(guild.id)[0][0]))
      guild_profile_lists.append(guild_front_page)

      # Members list
      member_data = []
      for member in guild.active_members:
        member_data.append((member.user.id, string_manipulation.truncate_string(member.user.username, 20), member.user.level, member.user.depth))

      member_data.sort(key=lambda x: x[0])

      member_table_strings = table2ascii(body=member_data, header=["ID", "Name", "Level", "Depth"], alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.RIGHT, Alignment.RIGHT]).split("\n")
      member_page_strings = []
      while member_table_strings:
        data_string, member_table_strings = string_manipulation.add_string_until_length(member_table_strings, 3000, "\n")
        member_page_strings.append(data_string)

      for member_page_string in member_page_strings:
        member_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 20)} members", color=disnake.Color.dark_blue(), description=f"```\n{member_page_string}\n```")
        message_utils.add_author_footer(member_page, inter.author)
        guild_profile_lists.append(member_page)

      # Event participation stats
      all_guild_participations = event_participation_repo.get_guild_event_participations_data(guild.id, ignore_zero_participation_median=True)
      all_guild_participation_amounts = [p[2] for p in all_guild_participations]
      if not all_guild_participation_amounts: all_guild_participation_amounts = [0]
      last_year_guild_participations_amounts = [p[2] for p in event_participation_repo.get_guild_event_participations_data(guild.id, current_year)]
      if not last_year_guild_participations_amounts: last_year_guild_participations_amounts = [0]

      guild_event_participations_stats_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 20)} event participations stats", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(guild_event_participations_stats_page, inter.author)
      guild_event_participations_stats_page.add_field(name="Average donate per event", value=f"{string_manipulation.format_number(statistics.mean(all_guild_participation_amounts), 1, scientific_notation_threshold=10)}", inline=False)
      guild_event_participations_stats_page.add_field(name="Median donate per event", value=f"{string_manipulation.format_number(statistics.median([p for p in all_guild_participation_amounts if p > 0]), 1, scientific_notation_threshold=10)}", inline=False)
      guild_event_participations_stats_page.add_field(name="Average donate per event last year", value=f"{string_manipulation.format_number(statistics.mean(last_year_guild_participations_amounts), 1, scientific_notation_threshold=10)}", inline=False)
      guild_event_participations_stats_page.add_field(name="Median donate per event last year", value=f"{string_manipulation.format_number(statistics.median([p for p in last_year_guild_participations_amounts if p > 0]), 1, scientific_notation_threshold=10)}", inline=False)
      guild_profile_lists.append(guild_event_participations_stats_page)

      # Event best contributors
      top_event_contributors = event_participation_repo.get_best_participants(guild.id, limit=10, ignore_zero_participation_median=True)
      top_event_contributors_data = [(idx + 1, string_manipulation.truncate_string(contributor[1], 14), string_manipulation.format_number(contributor[4]), string_manipulation.format_number(contributor[5], 1), string_manipulation.format_number(contributor[6], 1)) for idx, contributor in enumerate(top_event_contributors)]
      event_best_contributos_table_strings = table2ascii(body=top_event_contributors_data, header=["No°", "Name", "Total", "Average", "Median"], alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.RIGHT, Alignment.RIGHT, Alignment.RIGHT], first_col_heading=True).split("\n")

      event_best_contributos_page_strings = []
      while event_best_contributos_table_strings:
        data_string, event_participations_strings = string_manipulation.add_string_until_length(event_best_contributos_table_strings, 3000, "\n")
        event_best_contributos_page_strings.append(data_string)

      for event_best_contributos_page_string in event_best_contributos_page_strings:
        best_event_contributors_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 20)} best event contributors", color=disnake.Color.dark_blue(), description=f"```\n{event_best_contributos_page_string}\n```")
        message_utils.add_author_footer(best_event_contributors_page, inter.author)
        guild_profile_lists.append(best_event_contributors_page)

      # Event participations
      event_participations_data = []
      for year, week, total, average, median, _, _ in all_guild_participations:
        best_participants = event_participation_repo.get_best_participants(guild.id, year, week, limit=1) if total != 0 else None
        event_participations_data.append((year, week, (string_manipulation.truncate_string(best_participants[0][1], 14) if best_participants is not None else "*Unknown*"), string_manipulation.format_number(best_participants[0][4]) if best_participants else "0", string_manipulation.format_number(average, 1), string_manipulation.format_number(median, 1)))

      event_participations_strings = table2ascii(body=event_participations_data, header=["Year", "Week", "Top Member", "Top Donate", "Average", "Median"], alignments=[Alignment.RIGHT, Alignment.RIGHT, Alignment.LEFT, Alignment.RIGHT, Alignment.RIGHT, Alignment.RIGHT]).split("\n")
      event_participations_page_strings = []
      while event_participations_strings:
        data_string, event_participations_strings = string_manipulation.add_string_until_length(event_participations_strings, 3000, "\n")
        event_participations_page_strings.append(data_string)

      for event_participations_page_string in event_participations_page_strings:
        event_participation_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 20)} event participations", color=disnake.Color.dark_blue(), description=f"```\n{event_participations_page_string}\n```")
        message_utils.add_author_footer(event_participation_page, inter.author)
        guild_profile_lists.append(event_participation_page)

      guild_profiles.append(guild_profile_lists)

    embed_view = EmbedView2D(inter.author, guild_profiles, invert_list_dir=True)
    await embed_view.run(inter)

  @guild_commands.sub_command(name="event_participations", description=Strings.public_interface_guild_participations_description)
  @cooldowns.default_cooldown
  async def guild_event_participations(self, inter: disnake.CommandInteraction, identifier: str = commands.Param(description=Strings.dt_guild_identifier_param_description)):
    await inter.response.defer(with_message=True)

    guilds = dt_guild_repo.get_dt_guilds_by_identifier(identifier)

    if not guilds:
      await message_utils.generate_error_message(inter, Strings.public_interface_guild_data_not_found(identifier=identifier))
      return None

    pages = []
    for guild in guilds:
      all_guild_participations = event_participation_repo.get_guild_event_participations_data(guild.id, ignore_zero_participation_median=True)

      event_participations_data = []
      for year, week, total, average, median, _, _ in all_guild_participations:
        best_participants = event_participation_repo.get_best_participants(guild.id, year, week, limit=1) if total != 0 else None
        event_participations_data.append((year, week, (string_manipulation.truncate_string(best_participants[0][1], 14) if best_participants is not None else "*Unknown*"), string_manipulation.format_number(best_participants[0][4]) if best_participants else "0", string_manipulation.format_number(average, 1), string_manipulation.format_number(median, 1)))

      event_participations_strings = table2ascii(body=event_participations_data, header=["Year", "Week", "Top Member", "Top Donate", "Average", "Median"], alignments=[Alignment.RIGHT, Alignment.RIGHT, Alignment.LEFT, Alignment.RIGHT, Alignment.RIGHT, Alignment.RIGHT]).split("\n")
      event_participations_page_strings = []
      while event_participations_strings:
        data_string, event_participations_strings = string_manipulation.add_string_until_length(event_participations_strings, 3000, "\n")
        event_participations_page_strings.append(data_string)

      guild_participation_pages = []
      for event_participations_page_string in event_participations_page_strings:
        event_participation_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 20)} event participations", color=disnake.Color.dark_blue(), description=f"```\n{event_participations_page_string}\n```")
        message_utils.add_author_footer(event_participation_page, inter.author)
        guild_participation_pages.append(event_participation_page)

      pages.append(guild_participation_pages)

    embed_view = EmbedView2D(inter.author, pages, invert_list_dir=True)
    await embed_view.run(inter)

  @guild_commands.sub_command(name="leaderboard", description=Strings.public_interface_guild_leaderboard_description)
  @cooldowns.default_cooldown
  async def guild_leaderboard(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    guild_leaderboard_data = dt_guild_repo.get_guild_level_leaderboard()
    if not guild_leaderboard_data:
      return await message_utils.generate_error_message(inter, Strings.public_interface_guild_leaderboard_no_guilds)

    standing_table_data = []
    for standing, guild_id, guild_name, level in guild_leaderboard_data:
      member_number = dt_guild_member_repo.get_number_of_members(guild_id)
      standing_table_data.append((standing, string_manipulation.truncate_string(guild_name, 20), level, member_number))

    standing_table_strings = table2ascii(["No°", "Name", "Level", "Members"], standing_table_data, alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.RIGHT, Alignment.RIGHT], first_col_heading=True).split("\n")

    standing_pages = []
    while standing_table_strings:
      description, standing_table_strings = string_manipulation.add_string_until_length(standing_table_strings, 2000, "\n")

      embed = disnake.Embed(title="Deep Town Guilds Leaderboard", color=disnake.Color.dark_blue(), description=f"```\n{description}\n```")
      message_utils.add_author_footer(embed, inter.author)
      standing_pages.append(embed)

    embed_view = EmbedView(inter.author, standing_pages)
    await embed_view.run(inter)

  @commands.slash_command(name="user")
  async def user_command(self, inter: disnake.CommandInteraction):
    pass

  @user_command.sub_command(name="event_participations", description=Strings.public_interface_user_event_participations_description)
  @cooldowns.default_cooldown
  async def user_event_participations(self, inter: disnake.CommandInteraction, identifier: str=commands.Param(description=Strings.dt_user_identifier_param_description)):
    await inter.response.defer(with_message=True)

    matched_users = dt_user_repo.get_users_by_identifier(identifier)
    if not matched_users:
      return await message_utils.generate_error_message(inter, Strings.public_interface_user_profile_no_users(username=identifier))

    pages = []
    for user in matched_users:
      all_participations = event_participation_repo.get_event_participations(user_id=user.id)

      user_participations = []
      participation_pages_data = dt_report_generators.generate_participations_page_strings(all_participations)
      for participation_page_data in participation_pages_data:
        participation_page = disnake.Embed(title=f"{string_manipulation.truncate_string(user.username, 20)} ({user.id}) event participations", description=f"```\n{participation_page_data}\n```", color=disnake.Color.dark_blue())
        message_utils.add_author_footer(participation_page, inter.author)
        user_participations.append(participation_page)
      pages.append(user_participations)

    embed_view = EmbedView2D(inter.author, pages, invert_list_dir=True)
    await embed_view.run(inter)

  @user_command.sub_command(name="profile", description=Strings.public_interface_user_profile_description)
  @cooldowns.default_cooldown
  async def user_profile(self, inter: disnake.CommandInteraction, identifier:str=commands.Param(description=Strings.dt_user_identifier_param_description)):
    await inter.response.defer(with_message=True)

    matched_users = dt_user_repo.get_users_by_identifier(identifier)
    if not matched_users:
      return await message_utils.generate_error_message(inter, Strings.public_interface_user_profile_no_users(identifier=identifier))

    current_time = datetime.datetime.utcnow()
    current_year, _ = dt_helpers.get_event_index(current_time)

    user_profiles = []
    for user in matched_users:
      user_profile_lists = []

      guild_data = (await dt_helpers.get_dt_guild_data(self.bot, user.active_member.guild.id)) if user.active_member else None
      if guild_data is not None:
        event_participation_repo.generate_or_update_event_participations(guild_data)
        user = dt_user_repo.get_dt_user(user.id)

      all_participations = event_participation_repo.get_event_participations(user_id=user.id)
      all_participations_amounts = [p.amount for p in all_participations]
      if not all_participations_amounts: all_participations_amounts = [0]
      this_year_participations_amounts = [p.amount for p in event_participation_repo.get_event_participations(user_id=user.id, year=current_year)]
      if not this_year_participations_amounts: this_year_participations_amounts = [0]

      # Front page
      user_front_page = disnake.Embed(title=f"{string_manipulation.truncate_string(user.username, 20)}", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(user_front_page, inter.author)
      user_front_page.add_field(name="ID", value=str(user.id))
      user_front_page.add_field(name="Level", value=str(user.level))
      user_front_page.add_field(name="Depth", value=str(user.depth))
      user_front_page.add_field(name="Online", value=humanize.naturaltime(current_time - user.last_online) if user.last_online is not None else "Never")
      user_front_page.add_field(name="Current guild", value=f"{user.active_member.guild.name}({user.active_member.guild.level})" if user.active_member is not None else "None", inline=False)
      user_profile_lists.append(user_front_page)

      # Buildings page
      user_buildings_page = disnake.Embed(title=f"{string_manipulation.truncate_string(user.username, 20)} buildings", color=disnake.Color.dark_blue())
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

      # Event participation stats
      user_event_participations_stats_page = disnake.Embed(title=f"{string_manipulation.truncate_string(user.username, 20)} event participations stats", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(user_event_participations_stats_page, inter.author)
      user_event_participations_stats_page.add_field(name="Average donate", value=string_manipulation.format_number(statistics.mean(all_participations_amounts), 1, scientific_notation_threshold=10))
      user_event_participations_stats_page.add_field(name="Median donate", value=string_manipulation.format_number(statistics.median([p for p in all_participations_amounts if p > 0]), 1, scientific_notation_threshold=10), inline=False)
      user_event_participations_stats_page.add_field(name="Average donate last year", value=string_manipulation.format_number(statistics.mean(this_year_participations_amounts), 1, scientific_notation_threshold=10))
      user_event_participations_stats_page.add_field(name="Median donate last year", value=string_manipulation.format_number(statistics.median([p for p in this_year_participations_amounts if p > 0]), 1, scientific_notation_threshold=10), inline=False)
      user_profile_lists.append(user_event_participations_stats_page)

      # Event participations
      participation_pages_data = dt_report_generators.generate_participations_page_strings(all_participations)
      for participation_page_data in participation_pages_data:
        participation_page = disnake.Embed(title=f"{string_manipulation.truncate_string(user.username, 20)} event participations", description=f"```\n{participation_page_data}\n```", color=disnake.Color.dark_blue())
        message_utils.add_author_footer(participation_page, inter.author)
        user_profile_lists.append(participation_page)

      user_profiles.append(user_profile_lists)

    embed_view = EmbedView2D(inter.author, user_profiles, invert_list_dir=True)
    await embed_view.run(inter)

  @commands.slash_command(name="event")
  async def event_commands(self, inter: disnake.CommandInteraction):
    pass

  @event_commands.sub_command(name="help", description=Strings.public_interface_event_help_description)
  @cooldowns.default_cooldown
  async def event_help(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    year, week = dt_helpers.get_event_index(datetime.datetime.utcnow())
    event_specification = event_participation_repo.get_or_create_event_specification(year, week)

    item_table = dt_report_generators.get_event_items_table(event_specification)
    if item_table is None:
      return await message_utils.generate_error_message(inter, Strings.public_interface_event_help_no_items)

    await inter.send(f"```\nYear: {year} Week: {week}\n{item_table}\n```")

  @event_commands.sub_command_group(name="leaderboard")
  async def event_leaderboard(self, inter: disnake.CommandInteraction):
    pass

  @event_leaderboard.sub_command(name="current", description=Strings.public_interface_event_leaderboard_current_description)
  @cooldowns.default_cooldown
  async def global_event_current_leaderboard(self, inter: disnake.CommandInteraction,
                                             user_count: int=commands.Param(default=20, min_value=1, max_value=200, description=Strings.public_interface_event_leaderboard_current_user_count_param_description)):
    await inter.response.defer(with_message=True)
    event_year, event_week = dt_helpers.get_event_index(datetime.datetime.utcnow())
    await send_event_leaderboards(inter, event_year, event_week, user_count)

  @event_leaderboard.sub_command(name="specific", description=Strings.public_interface_event_leaderboard_specific_description)
  @cooldowns.default_cooldown
  async def global_event_current_leaderboard(self, inter: disnake.CommandInteraction,
                                             year: int=commands.Param(description=Strings.public_interface_event_leaderboard_specific_year_param_description),
                                             week: int=commands.Param(min_value=1, description=Strings.public_interface_event_leaderboard_specific_week_param_description),
                                             user_count: int = commands.Param(default=20, min_value=1, max_value=200, description=Strings.public_interface_event_leaderboard_specific_user_count_param_description)):
    await inter.response.defer(with_message=True)
    await send_event_leaderboards(inter, year, week, user_count)

def setup(bot):
  bot.add_cog(PublicInterface(bot))