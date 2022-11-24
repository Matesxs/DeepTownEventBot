import disnake
from disnake.ext import commands, tasks
from typing import Optional, List, Union
import math
import datetime
import asyncio

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from utils import dt_helpers, message_utils, permission_helper, string_manipulation
from database import event_participation_repo, tracking_settings_repo
from config import Strings, cooldowns, config
from features.paginator import EmbedView

logger = setup_custom_logger(__name__)


def generate_announce_report(participations: List[event_participation_repo.EventParticipation]) -> List[str]:
  participation_strings = [f"{ participations[0].dt_guild.name} - ID: {participations[0].dt_guild.id} - Level: {participations[0].dt_guild.level}\nYear: {participations[0].year} Week: {participations[0].event_week}\n\nName                        Level       Donate"]
  for participation in participations:
    padding_name = " " * max((28 - len(participation.user.username)), 1)
    padding_level = " " * max((12 - len(str(participation.user.level))), 1)
    participation_strings.append(f"{participation.user.username}{padding_name}{participation.user.level}{padding_level}{participation.amount}")

  announce_strings = []
  while participation_strings:
    final_string, participation_strings = string_manipulation.add_string_until_length(participation_strings, 2000, "\n")
    announce_strings.append(f"```py\n{final_string}\n```")

  return announce_strings

async def send_guild_report(report_channel: Union[disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable, disnake.CommandInteraction, commands.Context], dt_guild_id: int):
  participations = event_participation_repo.get_recent_event_participation(dt_guild_id)
  if not participations: return

  strings = generate_announce_report(participations)
  for string in strings:
    await report_channel.send(string)

class DTEventTracker(Base_Cog):
  def __init__(self, bot):
    super(DTEventTracker, self).__init__(bot, __file__)
    self.first_loop = True
    if not self.result_announce_task.is_running():
      self.result_announce_task.start()

  def cog_unload(self) -> None:
    if self.result_announce_task.is_running():
      self.result_announce_task.cancel()

  @commands.slash_command()
  async def reporter(self, inter: disnake.CommandInteraction):
    pass

  @reporter.sub_command(description=Strings.event_data_tracker_add_or_modify_tracker_description)
  @commands.check(permission_helper.is_administrator)
  @cooldowns.default_cooldown
  @commands.guild_only()
  async def add_or_modify_tracker(self, inter: disnake.CommandInteraction,
                                  guild_id: int=commands.Param(description="Deep Town Guild ID"),
                                  announce_channel:Optional[disnake.TextChannel]=commands.Param(default=None, description="Channel for announcing results at the end of event")):
    await inter.response.defer(with_message=True, ephemeral=True)

    data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
    if data is None:
      return await message_utils.generate_error_message(inter, Strings.event_data_tracker_add_or_modify_tracker_failed_to_get_data)

    event_participation_repo.generate_or_update_event_participations(data)
    tracking_settings_repo.get_or_create_tracking_settings(inter.guild, data, announce_channel.id if announce_channel is not None else None)

    if announce_channel is None:
      await message_utils.generate_success_message(inter, Strings.event_data_tracker_add_or_modify_tracker_success_without_channel(guild=data.name))
    else:
      await message_utils.generate_success_message(inter, Strings.event_data_tracker_add_or_modify_tracker_success_with_channel(guild=data.name, channel=announce_channel.name))

  @reporter.sub_command(description=Strings.event_data_tracker_remove_tracker_description)
  @commands.check(permission_helper.is_administrator)
  @cooldowns.default_cooldown
  @commands.guild_only()
  async def remove_tracker(self, inter: disnake.CommandInteraction,
                                 guild_id: int=commands.Param(description="Deep Town Guild ID")):
    await inter.response.defer(with_message=True, ephemeral=True)

    settings = tracking_settings_repo.get_tracking_settings(inter.guild.id, guild_id)
    guild_name = settings.dt_guild.name

    if tracking_settings_repo.remove_tracking_settings(inter.guild.id, guild_id):
      await message_utils.generate_success_message(inter, Strings.event_data_tracker_remove_tracker_success(guild=guild_name))
    else:
      await message_utils.generate_error_message(inter, Strings.event_data_tracker_remove_tracker_failed(guild_id=guild_id))

  @reporter.sub_command(description=Strings.event_data_tracker_list_trackers_description)
  @commands.check(permission_helper.is_administrator)
  @cooldowns.default_cooldown
  async def list_guild_trackers(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    guild_trackers = tracking_settings_repo.get_all_guild_trackers(inter.guild.id)
    number_of_trackers = len(guild_trackers)

    if number_of_trackers == 0:
      return await message_utils.generate_error_message(inter, Strings.event_data_tracker_list_trackers_no_trackers)

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

  @reporter.sub_command(description=Strings.event_data_tracker_search_guilds_description)
  @cooldowns.long_cooldown
  async def search_guilds(self, inter: disnake.CommandInteraction, guild_name:Optional[str]=commands.Param(default=None, description="Guild name to search")):
    await inter.response.defer(with_message=True, ephemeral=True)

    found_guilds = await dt_helpers.get_guild_info(self.bot, guild_name)
    if found_guilds is None or not found_guilds:
      return await message_utils.generate_error_message(inter, Strings.event_data_tracker_search_guilds_no_guild_found)

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

  @reporter.sub_command(description=Strings.event_data_tracker_generate_announcements_description)
  @commands.check(permission_helper.is_administrator)
  @cooldowns.huge_cooldown
  @commands.guild_only()
  async def generate_announcements(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    trackers = tracking_settings_repo.get_all_guild_trackers(inter.guild.id)
    if not trackers:
      return await message_utils.generate_error_message(inter, Strings.event_data_tracker_generate_announcements_no_data)

    guild_ids = tracking_settings_repo.get_guild_tracked_guild_ids(inter.guild.id)
    for guild_id in guild_ids:
      data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
      if data is None: continue
      event_participation_repo.generate_or_update_event_participations(data)
      await asyncio.sleep(0.5)

    for tracker in trackers:
      await self.announce(tracker)
      await asyncio.sleep(0.5)

    await message_utils.generate_success_message(inter, Strings.event_data_tracker_generate_announcements_success)

  @reporter.sub_command(description=Strings.event_data_tracker_generate_announcements_description)
  @cooldowns.long_cooldown
  async def guild_report(self, inter: disnake.CommandInteraction, guild_id: int=commands.Param(description="Deep Town Guild ID")):
    await inter.response.defer(with_message=True)

    data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
    if data is None:
      return await message_utils.generate_error_message(inter, Strings.event_data_tracker_guild_report_no_data)

    event_participation_repo.generate_or_update_event_participations(data)

    await send_guild_report(inter, guild_id)

  async def announce(self, tracker: tracking_settings_repo.TrackingSettings):
    announce_channel = await tracker.get_announce_channel(self.bot)
    if announce_channel is None: return

    await send_guild_report(announce_channel, tracker.dt_guild_id)

  @tasks.loop(hours=24*7)
  async def result_announce_task(self):
    logger.info("Update before announcement starting")
    if not config.event_data_collector.monitor_all_guilds:
      guild_ids = tracking_settings_repo.get_tracked_guild_ids()
    else:
      guild_ids = await dt_helpers.get_ids_of_all_guilds(self.bot)

    if guild_ids is not None:
      for guild_id in guild_ids:
        data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
        if data is None: continue

        event_participation_repo.generate_or_update_event_participations(data)
        await asyncio.sleep(1)
    logger.info("Update before announcement finished")

    logger.info("Starting Announcement")
    trackers = tracking_settings_repo.get_all_trackers()
    for tracker in trackers:
      await self.announce(tracker)
      await asyncio.sleep(0.5)

  @result_announce_task.before_loop
  async def result_announce_wait_pretask(self):
    if self.first_loop:
      logger.info("Startup guild data pull starting")
      if not config.event_data_collector.monitor_all_guilds:
        guild_ids = tracking_settings_repo.get_tracked_guild_ids()
      else:
        guild_ids = await dt_helpers.get_ids_of_all_guilds(self.bot)

      if guild_ids is not None:
        for guild_id in guild_ids:
          data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
          if data is None: continue

          event_participation_repo.generate_or_update_event_participations(data)
          await asyncio.sleep(1)
      logger.info("Startup guild data pull finished")

      today = datetime.datetime.utcnow().replace(hour=8, minute=10, second=0, microsecond=0)
      next_monday = today + datetime.timedelta(days=today.weekday() % 7)
      if next_monday < datetime.datetime.utcnow():
        next_monday += datetime.timedelta(days=7)
      delta_to_next_monday = next_monday - datetime.datetime.utcnow()
      await asyncio.sleep(delta_to_next_monday.total_seconds())
      self.first_loop = False

def setup(bot):
  bot.add_cog(DTEventTracker(bot))
