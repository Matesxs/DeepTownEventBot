import asyncio
import disnake
from disnake.ext import commands
import datetime
from functools import partial
import humanize
from table2ascii import table2ascii, Alignment
import sqlalchemy

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from config import cooldowns, Strings
from utils import dt_helpers, dt_report_generators, message_utils, string_manipulation, dt_autocomplete
from features.views.paginator import EmbedView
from database import event_participation_repo, dt_user_repo, dt_guild_repo, dt_guild_member_repo
from features.views.data_selector import DataSelector

logger = setup_custom_logger(__name__)

class PublicInterface(Base_Cog):
  def __init__(self, bot):
    super(PublicInterface, self).__init__(bot, __file__)

  @commands.slash_command(name="guild")
  async def guild_commands(self, inter: disnake.CommandInteraction):
    pass

  @guild_commands.sub_command(name="report", description=Strings.public_interface_guild_report_description)
  @cooldowns.default_cooldown
  async def guild_report(self, inter: disnake.CommandInteraction,
                         identifier = commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_autocomplete.autocomplete_identifier_guild, converter=dt_autocomplete.guild_user_identifier_converter),
                         event_identifier = commands.Param(default=None, description=Strings.dt_event_identifier_param_description, autocomplete=dt_autocomplete.autocomplete_event_identifier, converter=dt_autocomplete.event_identifier_converter, convert_defaults=True),
                         tight_format: bool = commands.Param(default=False, description=Strings.public_interface_guild_report_tight_format_param_description)):
    await inter.response.defer(with_message=True)

    if identifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    guild_data = await event_participation_repo.get_event_participations(guild_id=identifier[1], year=event_identifier[0], week=event_identifier[1], order_by=[event_participation_repo.EventParticipation.amount.desc()])

    if not guild_data:
      return await message_utils.generate_error_message(inter, Strings.dt_event_data_not_found(year=event_identifier[0], week=event_identifier[1]))

    send_report_function = partial(dt_report_generators.send_text_guild_event_participation_report, inter, guild_data[0].dt_guild, guild_data, colm_padding=0 if tight_format else 1)

    reporter_settings = DataSelector(inter.author, ["ID", "Level", "Depth", "Online", "Standing"], ["No°", "Name", "Donate"], invisible=True)
    await reporter_settings.run(inter)
    ret = await reporter_settings.wait()

    if not ret:
      await send_report_function(reporter_settings.get_results())

  @guild_commands.sub_command(name="profile", description=Strings.public_interface_guild_profile_description)
  @cooldowns.long_cooldown
  async def guild_profile(self, inter: disnake.CommandInteraction,
                          identifier = commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_autocomplete.autocomplete_identifier_guild, converter=dt_autocomplete.guild_user_identifier_converter)):
    await inter.response.defer(with_message=True)

    if identifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    guild = await dt_guild_repo.get_dt_guild(identifier[1])
    if not guild:
      return await message_utils.generate_error_message(inter, Strings.dt_guild_not_found(identifier=identifier[1]))

    guild_profile_lists = []

    current_time = datetime.datetime.utcnow()
    current_year, _ = dt_helpers.get_event_index(current_time)

    # Front page
    guild_front_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 20)}", color=disnake.Color.dark_blue())
    message_utils.add_author_footer(guild_front_page, inter.author)
    guild_front_page.add_field(name="ID", value=str(guild.id))
    guild_front_page.add_field(name="Level", value=str(guild.level))
    guild_front_page.add_field(name="Members", value=str(len(guild.active_members)))
    guild_front_page.add_field(name="Active", value=str(guild.is_active))
    guild_front_page.add_field(name="Position", value=str(await dt_guild_repo.get_guild_position(guild.id)))
    guild_profile_lists.append(guild_front_page)

    # Members list
    member_data = []
    for member in guild.active_members:
      member_data.append((member.user.id, string_manipulation.truncate_string(member.user.username, 20), member.user.level, humanize.naturaltime(current_time - member.user.last_online) if member.user.last_online is not None else "Never"))

    member_data.sort(key=lambda x: x[0])

    member_table_strings = table2ascii(body=member_data, header=["ID", "Name", "Level", "Online"], alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.RIGHT, Alignment.LEFT]).split("\n")
    member_page_strings = []
    while member_table_strings:
      data_string, member_table_strings = string_manipulation.add_string_until_length(member_table_strings, 3000, "\n")
      member_page_strings.append(data_string)

    for member_page_string in member_page_strings:
      member_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 20)} members", color=disnake.Color.dark_blue(), description=f"```\n{member_page_string}\n```")
      message_utils.add_author_footer(member_page, inter.author)
      guild_profile_lists.append(member_page)

    # Event participation stats
    all_time_total, all_time_average, all_time_median = await event_participation_repo.get_event_participation_stats(guild_id=guild.id, ignore_zero_participation_median=True)
    all_time_total_last_year, all_time_average_last_year, all_time_median_last_year = await event_participation_repo.get_event_participation_stats(guild_id=guild.id, year=current_year, ignore_zero_participation_median=True)

    guild_event_participations_stats_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 20)} event participations stats", color=disnake.Color.dark_blue())
    message_utils.add_author_footer(guild_event_participations_stats_page, inter.author)
    guild_event_participations_stats_page.add_field(name="Total event participation", value=string_manipulation.format_number(all_time_total, 4), inline=False)
    guild_event_participations_stats_page.add_field(name="Average donate per event", value=string_manipulation.format_number(all_time_average, 4), inline=False)
    guild_event_participations_stats_page.add_field(name="Median donate per event", value=string_manipulation.format_number(all_time_median, 4), inline=False)
    guild_event_participations_stats_page.add_field(name="Total event participation current year", value=string_manipulation.format_number(all_time_total_last_year, 4), inline=False)
    guild_event_participations_stats_page.add_field(name="Average donate per event current year", value=string_manipulation.format_number(all_time_average_last_year, 4), inline=False)
    guild_event_participations_stats_page.add_field(name="Median donate per event current year", value=string_manipulation.format_number(all_time_median_last_year, 4), inline=False)
    guild_profile_lists.append(guild_event_participations_stats_page)

    await asyncio.sleep(0.1)

    # Event best contributors
    top_event_contributors = await event_participation_repo.get_event_participants_data(guild.id, limit=10, ignore_zero_participation_median=True, only_current_members=True, order_by=[sqlalchemy.func.avg(event_participation_repo.EventParticipation.amount).desc()])
    top_event_contributors_data = [(idx + 1, string_manipulation.truncate_string(contributor[1], 14), string_manipulation.format_number(contributor[4]), string_manipulation.format_number(contributor[5]), string_manipulation.format_number(contributor[6])) for idx, contributor in enumerate(top_event_contributors)]
    event_best_contributors_table_strings = table2ascii(body=top_event_contributors_data, header=["No°", "Name", "Total", "Average", "Median"], alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.RIGHT, Alignment.RIGHT, Alignment.RIGHT], first_col_heading=True).split("\n")

    while event_best_contributors_table_strings:
      data_string, event_best_contributors_table_strings = string_manipulation.add_string_until_length(event_best_contributors_table_strings, 3000, "\n")
      best_event_contributors_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 20)} best event contributors", color=disnake.Color.dark_blue(), description=f"```\n{data_string}\n```")
      message_utils.add_author_footer(best_event_contributors_page, inter.author)
      guild_profile_lists.append(best_event_contributors_page)

    await asyncio.sleep(0.1)

    # Worst event contributors
    worst_event_contributors = await event_participation_repo.get_event_participants_data(guild.id, limit=10, ignore_zero_participation_median=True, only_current_members=True, order_by=[sqlalchemy.func.avg(event_participation_repo.EventParticipation.amount)])
    worst_event_contributors_data = [(idx + 1, string_manipulation.truncate_string(contributor[1], 14), string_manipulation.format_number(contributor[4]), string_manipulation.format_number(contributor[5]), string_manipulation.format_number(contributor[6])) for idx, contributor in enumerate(worst_event_contributors)]
    event_worst_contributors_table_strings = table2ascii(body=worst_event_contributors_data, header=["No°", "Name", "Total", "Average", "Median"], alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.RIGHT, Alignment.RIGHT, Alignment.RIGHT], first_col_heading=True).split("\n")

    while event_worst_contributors_table_strings:
      data_string, event_worst_contributors_table_strings = string_manipulation.add_string_until_length(event_worst_contributors_table_strings, 3000, "\n")
      worst_event_contributors_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 20)} worst event contributors", color=disnake.Color.dark_blue(), description=f"```\n{data_string}\n```")
      message_utils.add_author_footer(worst_event_contributors_page, inter.author)
      guild_profile_lists.append(worst_event_contributors_page)

    await asyncio.sleep(0.1)

    # Event participations
    event_participations_data = []
    for year, week, total, average, median in (await event_participation_repo.get_guild_event_participations_data(guild.id, ignore_zero_participation_median=True)):
      best_participants = await event_participation_repo.get_event_participants_data(guild.id, year, week, limit=1) if total != 0 else None
      event_participations_data.append((year, week, (string_manipulation.truncate_string(best_participants[0][1], 10) if best_participants is not None else "N/A"), string_manipulation.format_number(best_participants[0][4]) if best_participants else "0", string_manipulation.format_number(average), string_manipulation.format_number(median)))

    event_participations_strings = table2ascii(body=event_participations_data, header=["Year", "Week", "Top Member", "Top Donate", "Average", "Median"], alignments=[Alignment.RIGHT, Alignment.RIGHT, Alignment.LEFT, Alignment.RIGHT, Alignment.RIGHT, Alignment.RIGHT]).split("\n")
    while event_participations_strings:
      data_string, event_participations_strings = string_manipulation.add_string_until_length(event_participations_strings, 3000, "\n")
      event_participation_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 20)} event participations", color=disnake.Color.dark_blue(), description=f"```\n{data_string}\n```")
      message_utils.add_author_footer(event_participation_page, inter.author)
      guild_profile_lists.append(event_participation_page)

    embed_view = EmbedView(inter.author, guild_profile_lists)
    await embed_view.run(inter)

  @guild_commands.sub_command(name="event_participations", description=Strings.public_interface_guild_participations_description)
  @cooldowns.long_cooldown
  async def guild_event_participations(self, inter: disnake.CommandInteraction,
                                       identifier = commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_autocomplete.autocomplete_identifier_guild, converter=dt_autocomplete.guild_user_identifier_converter)):
    await inter.response.defer(with_message=True)

    if identifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    guild = await dt_guild_repo.get_dt_guild(identifier[1])
    if not guild:
      return await message_utils.generate_error_message(inter, Strings.dt_guild_not_found(identifier=identifier[1]))

    all_guild_participations = await event_participation_repo.get_guild_event_participations_data(guild.id, ignore_zero_participation_median=True)

    event_participations_data = []
    for year, week, total, average, median in all_guild_participations:
      best_participants = await event_participation_repo.get_event_participants_data(guild.id, year, week, limit=1) if total != 0 else None
      event_participations_data.append((year, week, (string_manipulation.truncate_string(best_participants[0][1], 10) if best_participants is not None else "N/A"), string_manipulation.format_number(best_participants[0][4]) if best_participants else "0", string_manipulation.format_number(average), string_manipulation.format_number(median)))

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

    embed_view = EmbedView(inter.author, guild_participation_pages)
    await embed_view.run(inter)

  @guild_commands.sub_command(name="leaderboard", description=Strings.public_interface_guild_leaderboard_description)
  @cooldowns.huge_cooldown
  async def guild_leaderboard(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    guild_leaderboard_data = await dt_guild_repo.get_guild_level_leaderboard()
    if not guild_leaderboard_data:
      return await message_utils.generate_error_message(inter, Strings.public_interface_guild_leaderboard_no_guilds)

    standing_table_data = []
    for standing, guild_id, guild_name, level in guild_leaderboard_data:
      member_number = await dt_guild_member_repo.get_number_of_members(guild_id)
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
  @cooldowns.long_cooldown
  async def user_event_participations(self, inter: disnake.CommandInteraction,
                                      identifier=commands.Param(description=Strings.dt_user_identifier_param_description, autocomp=dt_autocomplete.autocomplete_identifier_user, converter=dt_autocomplete.guild_user_identifier_converter)):
    await inter.response.defer(with_message=True)

    if identifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    user = await dt_user_repo.get_dt_user(identifier[1])
    if not user:
      return await message_utils.generate_error_message(inter, Strings.dt_user_not_found(identifier=identifier[1]))

    all_participations = await event_participation_repo.get_event_participations(user_id=user.id)

    user_participations = []
    participation_pages_data = dt_report_generators.generate_participations_page_strings(all_participations)
    for participation_page_data in participation_pages_data:
      participation_page = disnake.Embed(title=f"{string_manipulation.truncate_string(user.username, 20)} ({user.id}) event participations", description=f"```\n{participation_page_data}\n```", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(participation_page, inter.author)
      user_participations.append(participation_page)

    embed_view = EmbedView(inter.author, user_participations)
    await embed_view.run(inter)

  @user_command.sub_command(name="profile", description=Strings.public_interface_user_profile_description)
  @cooldowns.long_cooldown
  async def user_profile(self, inter: disnake.CommandInteraction,
                         identifier=commands.Param(description=Strings.dt_user_identifier_param_description, autocomp=dt_autocomplete.autocomplete_identifier_user, converter=dt_autocomplete.guild_user_identifier_converter)):
    await inter.response.defer(with_message=True)

    if identifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    user = await dt_user_repo.get_dt_user(identifier[1])
    if not user:
      return await message_utils.generate_error_message(inter, Strings.dt_user_not_found(identifier=identifier[1]))

    current_time = datetime.datetime.utcnow()
    current_year, _ = dt_helpers.get_event_index(current_time)

    user_profile_lists = []

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
    all_time_total, all_time_average, all_time_median = await event_participation_repo.get_event_participation_stats(user_id=user.id, ignore_zero_participation_median=True)
    all_time_total_last_year, all_time_average_last_year, all_time_median_last_year = await event_participation_repo.get_event_participation_stats(user_id=user.id, year=current_year, ignore_zero_participation_median=True)

    user_event_participations_stats_page = disnake.Embed(title=f"{string_manipulation.truncate_string(user.username, 20)} event participations stats", color=disnake.Color.dark_blue())
    message_utils.add_author_footer(user_event_participations_stats_page, inter.author)
    user_event_participations_stats_page.add_field(name="Total event participation", value=string_manipulation.format_number(all_time_total, 4), inline=False)
    user_event_participations_stats_page.add_field(name="Average donate", value=string_manipulation.format_number(all_time_average, 4), inline=False)
    user_event_participations_stats_page.add_field(name="Median donate", value=string_manipulation.format_number(all_time_median, 4), inline=False)
    user_event_participations_stats_page.add_field(name="Total event participation current year", value=string_manipulation.format_number(all_time_total_last_year, 4), inline=False)
    user_event_participations_stats_page.add_field(name="Average donate current year", value=string_manipulation.format_number(all_time_average_last_year, 4), inline=False)
    user_event_participations_stats_page.add_field(name="Median donate current year", value=string_manipulation.format_number(all_time_median_last_year, 4), inline=False)
    user_profile_lists.append(user_event_participations_stats_page)

    # Event participations
    participation_pages_data = dt_report_generators.generate_participations_page_strings(await event_participation_repo.get_event_participations(user_id=user.id))
    for participation_page_data in participation_pages_data:
      participation_page = disnake.Embed(title=f"{string_manipulation.truncate_string(user.username, 20)} event participations", description=f"```\n{participation_page_data}\n```", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(participation_page, inter.author)
      user_profile_lists.append(participation_page)

    embed_view = EmbedView(inter.author, user_profile_lists)
    await embed_view.run(inter)

  @commands.slash_command(name="event")
  async def event_commands(self, inter: disnake.CommandInteraction):
    pass

  @event_commands.sub_command(name="help", description=Strings.public_interface_event_help_description)
  @cooldowns.default_cooldown
  async def event_help(self, inter: disnake.CommandInteraction,
                       event_identifier = commands.Param(default=None, description=Strings.dt_event_identifier_param_description, autocomplete=dt_autocomplete.autocomplete_event_identifier, converter=dt_autocomplete.event_identifier_converter, convert_defaults=True),
                       materials_amounts: bool = commands.Param(default=False, description=Strings.public_interface_event_help_materials_amounts_param_description)):
    await inter.response.defer(with_message=True)

    event_specification = await event_participation_repo.get_event_specification(event_identifier[0], event_identifier[1])
    if event_specification is None:
      return await message_utils.generate_error_message(inter, Strings.public_interface_event_help_no_items)

    item_table = dt_report_generators.get_event_items_table(event_specification)
    if item_table is None:
      return await message_utils.generate_error_message(inter, Strings.public_interface_event_help_no_items)

    await inter.send(f"```\nYear: {event_identifier[0]} Week: {event_identifier[1]}\n{item_table}\n```")

    if materials_amounts:
      event_items_scaling_table = dt_report_generators.get_event_items_scaling_table(event_specification)
      if event_items_scaling_table is not None:
        event_items_scaling_table_lines = event_items_scaling_table.split("\n")
        while event_items_scaling_table_lines:
          final_string, event_items_scaling_table_lines = string_manipulation.add_string_until_length(event_items_scaling_table_lines, 1800, "\n")
          await inter.send(f"```\n{final_string}\n```")
      else:
        await message_utils.generate_error_message(inter, Strings.public_interface_event_help_no_item_amount_scaling)

  @event_commands.sub_command(name="leaderboard", description=Strings.public_interface_event_leaderboard_specific_description)
  @cooldowns.huge_cooldown
  async def global_event_leaderboard(self, inter: disnake.CommandInteraction,
                                             event_identifier = commands.Param(default=None, description=Strings.dt_event_identifier_param_description, autocomplete=dt_autocomplete.autocomplete_event_identifier, converter=dt_autocomplete.event_identifier_converter, convert_defaults=True),
                                             user_count: int = commands.Param(default=20, min_value=1, max_value=200, description=Strings.public_interface_event_leaderboard_specific_user_count_param_description)):
    await inter.response.defer(with_message=True)

    global_best_participants = await event_participation_repo.get_event_participants_data(year=event_identifier[0], week=event_identifier[1], limit=user_count)
    if not global_best_participants:
      return await message_utils.generate_error_message(inter, Strings.dt_event_data_not_found(year=event_identifier[0], week=event_identifier[1]))

    participant_data = [(idx + 1, string_manipulation.truncate_string(username, 20), string_manipulation.truncate_string(guild_name, 20), string_manipulation.format_number(total_contribution)) for idx, (_, username, _, guild_name, total_contribution, _, _) in enumerate(global_best_participants)]
    participant_data_table_strings = (f"Year: {event_identifier[0]} Week: {event_identifier[1]}\n" + table2ascii(header=["No°", "Username", "Guild", "Donate"], body=participant_data, first_col_heading=True, alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.LEFT, Alignment.RIGHT])).split("\n")

    while participant_data_table_strings:
      data_string, participant_data_table_strings = string_manipulation.add_string_until_length(participant_data_table_strings, 1900, "\n")
      await inter.send(f"```\n{data_string}\n```")

def setup(bot):
  bot.add_cog(PublicInterface(bot))