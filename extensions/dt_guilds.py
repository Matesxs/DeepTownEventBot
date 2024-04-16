import disnake
from disnake.ext import commands
from table2ascii import table2ascii, Alignment
from functools import partial
import sqlalchemy
import datetime
import asyncio

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from config import cooldowns, Strings
from utils import message_utils, dt_autocomplete, dt_report_generators, dt_helpers, string_manipulation
from utils.humanize_wrapper import hum_naturaltime
from database import event_participation_repo, dt_guild_repo, dt_guild_member_repo
from features.views.data_selector import DataSelector
from features.views.paginator import EmbedView

logger = setup_custom_logger(__name__)

class DTGuilds(Base_Cog):
  def __init__(self, bot):
    super(DTGuilds, self).__init__(bot, __file__)

  @commands.slash_command(name="guild")
  async def guild_commands(self, inter: disnake.CommandInteraction):
    pass

  @guild_commands.sub_command(name="report", description=Strings.public_interface_guild_report_description)
  @cooldowns.default_cooldown
  async def guild_report(self, inter: disnake.CommandInteraction,
                         modify_fields: bool = commands.Param(default=False, description=Strings.public_interface_guild_report_modify_fields_param_description),
                         identifier=commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_autocomplete.autocomplete_identifier_guild, converter=dt_autocomplete.guild_user_identifier_converter),
                         event_identifier=commands.Param(default=None, description=Strings.dt_event_identifier_param_description, autocomplete=dt_autocomplete.autocomplete_event_identifier, converter=dt_autocomplete.event_identifier_converter, convert_defaults=True),
                         tight_format: bool = commands.Param(default=False, description=Strings.public_interface_guild_report_tight_format_param_description)):
    if isinstance(inter.channel, (disnake.abc.GuildChannel, disnake.Thread)):
      if not inter.channel.permissions_for(inter.channel.guild.me).send_messages:
        res = await message_utils.generate_error_message(inter, Strings.error_bot_missing_permission)
        if res is None:
          await message_utils.generate_error_message(inter.author, Strings.error_bot_missing_permission)
        return

    await inter.response.defer(with_message=True)

    if identifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    guild_data = await event_participation_repo.get_event_participations(guild_id=identifier[1], year=event_identifier[0], week=event_identifier[1], order_by=[event_participation_repo.EventParticipation.amount.desc()])

    if not guild_data:
      return await message_utils.generate_error_message(inter, Strings.dt_event_data_not_found(year=event_identifier[0], week=event_identifier[1]))

    if modify_fields:
      send_report_function = partial(dt_report_generators.send_text_guild_event_participation_report, participations=guild_data, colm_padding=0 if tight_format else 1)

      reporter_settings = DataSelector(inter.author, ["No°", "Name", "Donate"], ["No°", "ID", "Name", "Level", "Depth", "Online", "Donate", "Standing"])
      await reporter_settings.run(inter)
      ret = await reporter_settings.wait()

      if not ret:
        await send_report_function(output=reporter_settings.message, colms=reporter_settings.get_results())
    else:
      await dt_report_generators.send_text_guild_event_participation_report(inter, guild_data, ["No°", "Name", "Donate"], colm_padding=0 if tight_format else 1)

  @guild_commands.sub_command(name="csv_report", description=Strings.public_interface_csv_guild_report_description)
  @cooldowns.default_cooldown
  async def guild_csv_report(self, inter: disnake.CommandInteraction,
                             identifier=commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_autocomplete.autocomplete_identifier_guild, converter=dt_autocomplete.guild_user_identifier_converter),
                             event_identifier=commands.Param(default=None, description=Strings.dt_event_identifier_param_description, autocomplete=dt_autocomplete.autocomplete_event_identifier, converter=dt_autocomplete.event_identifier_converter, convert_defaults=True)):
    await inter.response.defer(with_message=True)

    if identifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    guild_data = await event_participation_repo.get_event_participations(guild_id=identifier[1], year=event_identifier[0], week=event_identifier[1], order_by=[event_participation_repo.EventParticipation.amount.desc()])

    if not guild_data:
      return await message_utils.generate_error_message(inter, Strings.dt_event_data_not_found(year=event_identifier[0], week=event_identifier[1]))

    await dt_report_generators.send_csv_guild_event_participation_report(inter, guild_data[0].dt_guild, guild_data)

  @guild_commands.sub_command(name="profile", description=Strings.public_interface_guild_profile_description)
  @cooldowns.long_cooldown
  async def guild_profile(self, inter: disnake.CommandInteraction,
                          identifier=commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_autocomplete.autocomplete_identifier_guild, converter=dt_autocomplete.guild_user_identifier_converter)):
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
    guild_front_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 200)}", color=disnake.Color.dark_blue())
    message_utils.add_author_footer(guild_front_page, inter.author)
    guild_front_page.add_field(name="ID", value=str(guild.id))
    guild_front_page.add_field(name="Level", value=str(guild.level))
    guild_front_page.add_field(name="Members", value=str(len(guild.members)))
    guild_front_page.add_field(name="Active", value=str(guild.is_active))
    guild_front_page.add_field(name="Position", value=str(await dt_guild_repo.get_guild_position(guild.id)))
    guild_profile_lists.append(guild_front_page)

    # Members list
    member_data = []
    for member in guild.members:
      member_data.append((member.user.id, string_manipulation.truncate_string(member.user.username, 14), member.user.level, hum_naturaltime(current_time - member.user.last_online, only_first=True) if member.user.last_online is not None else "Never"))

    member_data.sort(key=lambda x: x[0])

    member_table_strings = table2ascii(body=member_data, header=["ID", "Name", "Level", "Online"], alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.RIGHT, Alignment.LEFT]).split("\n")
    member_page_strings = []
    while member_table_strings:
      data_string, member_table_strings = string_manipulation.add_string_until_length(member_table_strings, 4000, "\n", 42)
      member_page_strings.append(data_string)

    for member_page_string in member_page_strings:
      member_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 200)} members", color=disnake.Color.dark_blue(), description=f"```\n{member_page_string}\n```")
      message_utils.add_author_footer(member_page, inter.author)
      guild_profile_lists.append(member_page)

    # Event participation stats
    all_time_total, all_time_average, all_time_median = await event_participation_repo.get_event_participation_stats(guild_id=guild.id, ignore_zero_participation_median=True)
    all_time_total_last_year, all_time_average_last_year, all_time_median_last_year = await event_participation_repo.get_event_participation_stats(guild_id=guild.id, year=current_year, ignore_zero_participation_median=True)

    guild_event_participations_stats_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 200)} event participations stats", color=disnake.Color.dark_blue())
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
    top_event_contributors_data = [(string_manipulation.truncate_string(contributor[1], 14), string_manipulation.format_number(contributor[4]), string_manipulation.format_number(contributor[5])) for idx, contributor in enumerate(top_event_contributors)]
    event_best_contributors_table_strings = table2ascii(body=top_event_contributors_data, header=["Name", "Total", "Average"], alignments=[Alignment.LEFT, Alignment.RIGHT, Alignment.RIGHT]).split("\n")

    while event_best_contributors_table_strings:
      data_string, event_best_contributors_table_strings = string_manipulation.add_string_until_length(event_best_contributors_table_strings, 4000, "\n", 42)
      best_event_contributors_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 200)} best event contributors", color=disnake.Color.dark_blue(), description=f"```\n{data_string}\n```")
      message_utils.add_author_footer(best_event_contributors_page, inter.author)
      guild_profile_lists.append(best_event_contributors_page)

    await asyncio.sleep(0.1)

    # Worst event contributors
    worst_event_contributors = await event_participation_repo.get_event_participants_data(guild.id, limit=10, ignore_zero_participation_median=True, only_current_members=True, order_by=[sqlalchemy.func.avg(event_participation_repo.EventParticipation.amount)])
    worst_event_contributors_data = [(string_manipulation.truncate_string(contributor[1], 14), string_manipulation.format_number(contributor[4]), string_manipulation.format_number(contributor[5])) for idx, contributor in enumerate(worst_event_contributors)]
    event_worst_contributors_table_strings = table2ascii(body=worst_event_contributors_data, header=["Name", "Total", "Average"], alignments=[Alignment.LEFT, Alignment.RIGHT, Alignment.RIGHT]).split("\n")

    while event_worst_contributors_table_strings:
      data_string, event_worst_contributors_table_strings = string_manipulation.add_string_until_length(event_worst_contributors_table_strings, 4000, "\n", 42)
      worst_event_contributors_page = disnake.Embed(title=f"{string_manipulation.truncate_string(guild.name, 200)} worst event contributors", color=disnake.Color.dark_blue(), description=f"```\n{data_string}\n```")
      message_utils.add_author_footer(worst_event_contributors_page, inter.author)
      guild_profile_lists.append(worst_event_contributors_page)

    await asyncio.sleep(0.1)

    # Event participations
    guild_profile_lists.extend(await dt_report_generators.generate_guild_event_participation_pages(inter.author, guild))

    embed_view = EmbedView(inter.author, guild_profile_lists)
    await embed_view.run(inter)

  @guild_commands.sub_command(name="event_participations", description=Strings.public_interface_guild_participations_description)
  @cooldowns.long_cooldown
  async def guild_event_participations(self, inter: disnake.CommandInteraction,
                                       identifier=commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_autocomplete.autocomplete_identifier_guild, converter=dt_autocomplete.guild_user_identifier_converter)):
    await inter.response.defer(with_message=True)

    if identifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    guild = await dt_guild_repo.get_dt_guild(identifier[1])
    if not guild:
      return await message_utils.generate_error_message(inter, Strings.dt_guild_not_found(identifier=identifier[1]))

    guild_participation_pages = await dt_report_generators.generate_guild_event_participation_pages(inter.author, guild)

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
      description, standing_table_strings = string_manipulation.add_string_until_length(standing_table_strings, 4000, "\n", 42)

      embed = disnake.Embed(title="Deep Town Guilds Leaderboard", color=disnake.Color.dark_blue(), description=f"```\n{description}\n```")
      message_utils.add_author_footer(embed, inter.author)
      standing_pages.append(embed)

    embed_view = EmbedView(inter.author, standing_pages)
    await embed_view.run(inter)

def setup(bot):
  bot.add_cog(DTGuilds(bot))
