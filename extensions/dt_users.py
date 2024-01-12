import asyncio
import disnake
from disnake.ext import commands
import datetime
import humanize

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from config import cooldowns, Strings
from utils import dt_helpers, dt_report_generators, message_utils, string_manipulation, dt_autocomplete
from features.views.paginator import EmbedView
from database import event_participation_repo, dt_user_repo

logger = setup_custom_logger(__name__)

class DTUsers(Base_Cog):
  def __init__(self, bot):
    super(DTUsers, self).__init__(bot, __file__)

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
      participation_page = disnake.Embed(title=f"{string_manipulation.truncate_string(user.username, 200)} event participations", description=f"```\n{participation_page_data}\n```", color=disnake.Color.dark_blue())
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
    user_front_page = disnake.Embed(title=f"{string_manipulation.truncate_string(user.username, 200)}", color=disnake.Color.dark_blue())
    message_utils.add_author_footer(user_front_page, inter.author)
    user_front_page.add_field(name="ID", value=str(user.id))
    user_front_page.add_field(name="Level", value=str(user.level))
    user_front_page.add_field(name="Depth", value=str(user.depth))
    user_front_page.add_field(name="Online", value=humanize.naturaltime(current_time - user.last_online) if user.last_online is not None else "Never")
    user_front_page.add_field(name="Active", value=str(user.is_active))
    user_front_page.add_field(name="Current guild", value=f"{user.members[0].guild.name}({user.members[0].dt_guild_id})" if user.members else "None", inline=False)
    user_profile_lists.append(user_front_page)

    # Buildings page
    user_buildings_page = disnake.Embed(title=f"{string_manipulation.truncate_string(user.username, 200)} buildings", color=disnake.Color.dark_blue())
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

    user_event_participations_stats_page = disnake.Embed(title=f"{string_manipulation.truncate_string(user.username, 200)} event participations stats", color=disnake.Color.dark_blue())
    message_utils.add_author_footer(user_event_participations_stats_page, inter.author)
    user_event_participations_stats_page.add_field(name="Total event participation", value=string_manipulation.format_number(all_time_total, 4), inline=False)
    user_event_participations_stats_page.add_field(name="Average donate", value=string_manipulation.format_number(all_time_average, 4), inline=False)
    user_event_participations_stats_page.add_field(name="Median donate", value=string_manipulation.format_number(all_time_median, 4), inline=False)
    user_event_participations_stats_page.add_field(name="Total event participation current year", value=string_manipulation.format_number(all_time_total_last_year, 4), inline=False)
    user_event_participations_stats_page.add_field(name="Average donate current year", value=string_manipulation.format_number(all_time_average_last_year, 4), inline=False)
    user_event_participations_stats_page.add_field(name="Median donate current year", value=string_manipulation.format_number(all_time_median_last_year, 4), inline=False)
    user_profile_lists.append(user_event_participations_stats_page)

    await asyncio.sleep(0.1)

    # Event participations
    participation_pages_data = dt_report_generators.generate_participations_page_strings(await event_participation_repo.get_event_participations(user_id=user.id))
    for participation_page_data in participation_pages_data:
      participation_page = disnake.Embed(title=f"{string_manipulation.truncate_string(user.username, 200)} event participations", description=f"```\n{participation_page_data}\n```", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(participation_page, inter.author)
      user_profile_lists.append(participation_page)

    embed_view = EmbedView(inter.author, user_profile_lists)
    await embed_view.run(inter)

def setup(bot):
  bot.add_cog(DTUsers(bot))