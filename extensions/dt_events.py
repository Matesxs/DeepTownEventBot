import disnake
from disnake.ext import commands
import datetime
from table2ascii import table2ascii, Alignment
from typing import Optional

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from config import cooldowns, Strings
from utils import dt_helpers, message_utils, dt_autocomplete, dt_report_generators, string_manipulation
from database import dt_items_repo, event_participation_repo
from features.views.paginator import EmbedView

logger = setup_custom_logger(__name__)

class DTEvents(Base_Cog):
  def __init__(self, bot):
    super(DTEvents, self).__init__(bot, __file__)

  @commands.slash_command(name="event")
  async def event_commands(self, inter: disnake.CommandInteraction):
    pass

  @event_commands.sub_command(name="current", description=Strings.public_interface_event_current_description)
  @cooldowns.default_cooldown
  async def current_event(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    year, week = dt_helpers.get_event_index(datetime.datetime.utcnow())
    start_date, end_date = dt_helpers.event_index_to_date_range(year, week)

    embed = disnake.Embed(title="Current event", color=disnake.Color.dark_blue(), description=f"`{year} {week}`\n{start_date.day}.{start_date.month}.{start_date.year} - {end_date.day}.{end_date.month}.{end_date.year}")
    message_utils.add_author_footer(embed, inter.author)

    await inter.send(embed=embed)

  @event_commands.sub_command(name="help", description=Strings.public_interface_event_help_description)
  @cooldowns.long_cooldown
  async def event_help(self, inter: disnake.CommandInteraction,
                       event_identifier=commands.Param(default=None, description=Strings.dt_event_identifier_param_description, autocomplete=dt_autocomplete.autocomplete_event_identifier, converter=dt_autocomplete.event_identifier_converter, convert_defaults=True),
                       item_scaling_levels: int = commands.Param(min_value=0, max_value=100, default=30, description=Strings.public_interface_event_help_item_scaling_levels_param_description)):
    if isinstance(inter.channel, (disnake.abc.GuildChannel, disnake.Thread)):
      if not inter.channel.permissions_for(inter.channel.guild.me).send_messages:
        res = await message_utils.generate_error_message(inter, Strings.error_bot_missing_permission)
        if res is None:
          await message_utils.generate_error_message(inter.author, Strings.error_bot_missing_permission)
        return

    await inter.response.defer(with_message=True)

    event_specification = await event_participation_repo.get_event_specification(event_identifier[0], event_identifier[1])
    if event_specification is None:
      return await message_utils.generate_error_message(inter, Strings.public_interface_event_help_no_items)

    item_table = dt_report_generators.get_event_items_table(event_specification)
    if item_table is None:
      return await message_utils.generate_error_message(inter, Strings.public_interface_event_help_no_items)

    start_date, end_date = dt_helpers.event_index_to_date_range(int(event_identifier[0]), int(event_identifier[1]))
    help_string = f"Year: {event_identifier[0]} Week: {event_identifier[1]}\n{start_date.day}.{start_date.month}.{start_date.year} - {end_date.day}.{end_date.month}.{end_date.year}\n{item_table}"

    if item_scaling_levels != 0:
      event_items_scaling_table = dt_report_generators.get_event_items_scaling_table(event_specification, levels=item_scaling_levels)
      if event_items_scaling_table is not None:
        help_string += f"\n{event_items_scaling_table}"
      else:
        await message_utils.generate_error_message(inter, Strings.public_interface_event_help_no_item_amount_scaling)

    help_string_lines = help_string.split("\n")
    while help_string_lines:
      final_string, help_string_lines = string_manipulation.add_string_until_length(help_string_lines, 1900, "\n")
      await inter.send(f"```\n{final_string}\n```")

  @event_commands.sub_command(name="history", description=Strings.public_interface_event_history_description)
  @cooldowns.long_cooldown
  async def event_items_history(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    event_item_history_data = await dt_items_repo.get_event_items_history()
    event_item_history_data = [(f"{item[0]} {item[1]}", item[2] if item[2] is not None else "N/A") for item in event_item_history_data]

    table_strings = table2ascii(["Event", "Items"], event_item_history_data, alignments=[Alignment.LEFT, Alignment.LEFT]).split("\n")
    pages = []
    while table_strings:
      final_string, table_strings = string_manipulation.add_string_until_length(table_strings, 4000, "\n", 42)

      embed = disnake.Embed(title="Event item history", color=disnake.Color.dark_blue(), description=f"```\n{final_string}\n```")
      message_utils.add_author_footer(embed, inter.author)
      pages.append(embed)

    if not pages:
      await message_utils.generate_error_message(inter, Strings.public_interface_event_history_no_events)
    else:
      embed_view = EmbedView(inter.author, pages)
      await embed_view.run(inter)

  @event_commands.sub_command(name="stats", description=Strings.public_interface_event_stats_description)
  @cooldowns.long_cooldown
  async def event_stat(self, inter: disnake.CommandInteraction,
                       year: Optional[int] = commands.Param(default=None, description=Strings.public_interface_event_stats_year_param_description, autocomplete=dt_autocomplete.autocomplete_event_year)):
    await inter.response.defer(with_message=True)

    data = await dt_items_repo.get_event_item_stats(year)
    if not data:
      return await message_utils.generate_error_message(inter, Strings.public_interface_event_stats_no_stats)

    table_lines = table2ascii(["Item", "Count", "Last"], data, alignments=[Alignment.LEFT, Alignment.RIGHT, Alignment.LEFT]).split("\n")

    pages = []
    while table_lines:
      final_string, table_lines = string_manipulation.add_string_until_length(table_lines, 4000, "\n", 42)

      embed = disnake.Embed(title="Event item statistics" if year is None else f"Event statistics for `{year}`", color=disnake.Color.dark_blue(), description=f"```\n{final_string}\n```")
      message_utils.add_author_footer(embed, inter.author)
      pages.append(embed)

    embed_view = EmbedView(inter.author, pages)
    await embed_view.run(inter)

  @event_commands.sub_command_group(name="leaderboard")
  async def leaderboard_commands(self, inter: disnake.CommandInteraction):
    pass

  @leaderboard_commands.sub_command(name="users", description=Strings.public_interface_event_leaderboard_users_description)
  @cooldowns.long_cooldown
  async def user_event_leaderboard(self, inter: disnake.CommandInteraction,
                                   event_identifier=commands.Param(default=None, description=Strings.dt_event_identifier_param_description, autocomplete=dt_autocomplete.autocomplete_event_identifier, converter=dt_autocomplete.event_identifier_converter, convert_defaults=True),
                                   limit: int = commands.Param(default=20, min_value=1, max_value=200, description=Strings.public_interface_event_leaderboard_limit_param_description)):
    if isinstance(inter.channel, (disnake.abc.GuildChannel, disnake.Thread)):
      if not inter.channel.permissions_for(inter.channel.guild.me).send_messages:
        res = await message_utils.generate_error_message(inter, Strings.error_bot_missing_permission)
        if res is None:
          await message_utils.generate_error_message(inter.author, Strings.error_bot_missing_permission)
        return

    await inter.response.defer(with_message=True)

    global_best_participants = await event_participation_repo.get_users_leaderboard(year=event_identifier[0], week=event_identifier[1], limit=limit)
    if not global_best_participants:
      return await message_utils.generate_error_message(inter, Strings.dt_event_data_not_found(year=event_identifier[0], week=event_identifier[1]))

    participant_data = [(idx + 1, string_manipulation.truncate_string(username, 20), string_manipulation.truncate_string(guild_name, 20), string_manipulation.format_number(total_contribution)) for idx, (username, guild_name, total_contribution) in enumerate(global_best_participants)]
    start_date, end_date = dt_helpers.event_index_to_date_range(int(event_identifier[0]), int(event_identifier[1]))
    participant_data_table_strings = (f"Year: {event_identifier[0]} Week: {event_identifier[1]}\n{start_date.day}.{start_date.month}.{start_date.year} - {end_date.day}.{end_date.month}.{end_date.year}\n" +
                                      table2ascii(header=["No°", "Username", "Guild", "Donate"], body=participant_data, first_col_heading=True, alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.LEFT, Alignment.RIGHT])
                                      ).split("\n")

    while participant_data_table_strings:
      data_string, participant_data_table_strings = string_manipulation.add_string_until_length(participant_data_table_strings, 1900, "\n")
      await inter.send(f"```\n{data_string}\n```")

  @leaderboard_commands.sub_command(name="guilds", description=Strings.public_interface_event_leaderboard_guilds_description)
  @cooldowns.long_cooldown
  async def guild_event_leaderboard(self, inter: disnake.CommandInteraction,
                                    event_identifier=commands.Param(default=None, description=Strings.dt_event_identifier_param_description, autocomplete=dt_autocomplete.autocomplete_event_identifier, converter=dt_autocomplete.event_identifier_converter, convert_defaults=True),
                                    limit: int = commands.Param(default=20, min_value=1, max_value=200, description=Strings.public_interface_event_leaderboard_limit_param_description)):
    if isinstance(inter.channel, (disnake.abc.GuildChannel, disnake.Thread)):
      if not inter.channel.permissions_for(inter.channel.guild.me).send_messages:
        res = await message_utils.generate_error_message(inter, Strings.error_bot_missing_permission)
        if res is None:
          await message_utils.generate_error_message(inter.author, Strings.error_bot_missing_permission)
        return

    await inter.response.defer(with_message=True)

    best_guilds = await event_participation_repo.get_guild_leaderbord(year=event_identifier[0], week=event_identifier[1], limit=limit)
    if not best_guilds:
      return await message_utils.generate_error_message(inter, Strings.dt_event_data_not_found(year=event_identifier[0], week=event_identifier[1]))

    participant_data = [(idx + 1, string_manipulation.truncate_string(guild_name, 20), string_manipulation.format_number(total_contribution), string_manipulation.format_number(max_contribution)) for idx, (guild_name, total_contribution, max_contribution) in enumerate(best_guilds)]
    start_date, end_date = dt_helpers.event_index_to_date_range(int(event_identifier[0]), int(event_identifier[1]))
    participant_data_table_strings = (f"Year: {event_identifier[0]} Week: {event_identifier[1]}\n{start_date.day}.{start_date.month}.{start_date.year} - {end_date.day}.{end_date.month}.{end_date.year}\n" +
                                      table2ascii(header=["No°", "Guild", "Donate", "Top Donate"], body=participant_data, first_col_heading=True, alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.RIGHT, Alignment.RIGHT])
                                      ).split("\n")

    while participant_data_table_strings:
      data_string, participant_data_table_strings = string_manipulation.add_string_until_length(participant_data_table_strings, 1900, "\n")
      await inter.send(f"```\n{data_string}\n```")

def setup(bot):
  bot.add_cog(DTEvents(bot))
