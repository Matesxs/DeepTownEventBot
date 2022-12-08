import disnake
from disnake.ext import commands, tasks
import math
import datetime
import asyncio
import humanize

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from utils import dt_helpers, dt_report_generators, message_utils, permission_helper
from database import event_participation_repo, tracking_settings_repo
from config import Strings, cooldowns, config
from features.views.paginator import EmbedView

logger = setup_custom_logger(__name__)

class DTEventTracker(Base_Cog):
  def __init__(self, bot):
    super(DTEventTracker, self).__init__(bot, __file__)
    if not self.result_announce_task.is_running():
      self.result_announce_task.start()

  def cog_unload(self) -> None:
    if self.result_announce_task.is_running():
      self.result_announce_task.cancel()

  @commands.slash_command()
  @commands.check(permission_helper.is_administrator)
  @commands.guild_only()
  async def tracker(self, inter: disnake.CommandInteraction):
    pass

  @tracker.sub_command(name="add_or_modify", description=Strings.event_data_tracker_add_or_modify_tracker_description)
  @cooldowns.default_cooldown
  async def add_or_modify_tracker(self, inter: disnake.CommandInteraction,
                                  guild_id: int=commands.Param(description=Strings.dt_guild_id_param_description),
                                  announce_channel: disnake.TextChannel=commands.Param(description=Strings.event_data_tracker_add_or_modify_tracker_announce_channel_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    existing_tracker = tracking_settings_repo.get_tracking_settings(inter.guild.id, guild_id)
    if not existing_tracker:
      all_trackers = tracking_settings_repo.get_all_guild_trackers(inter.guild.id)
      if self.bot.owner is None or inter.author.id != self.bot.owner.id:
        if len(all_trackers) >= config.event_tracker.tracker_limit_per_guild:
          return await message_utils.generate_error_message(inter, Strings.event_data_tracker_add_or_modify_tracker_tracker_limit_reached(limit=config.event_data_tracker.tracker_limit_per_guild))

      data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
      if data is None:
        return await message_utils.generate_error_message(inter, Strings.event_data_tracker_add_or_modify_tracker_failed_to_get_data)

      guild_name = data.name

      event_participation_repo.generate_or_update_event_participations(data)
      tracking_settings_repo.get_or_create_tracking_settings(inter.guild, data, announce_channel.id)
    else:
      guild_name = existing_tracker.dt_guild.name
      existing_tracker.announce_channel_id = str(announce_channel.id)
      tracking_settings_repo.session.commit()

    await message_utils.generate_success_message(inter, Strings.event_data_tracker_add_or_modify_tracker_success_with_channel(guild=guild_name, channel=announce_channel.name))

  @tracker.sub_command(name="remove", description=Strings.event_data_tracker_remove_tracker_description)
  @cooldowns.default_cooldown
  async def remove_tracker(self, inter: disnake.CommandInteraction,
                                 guild_id: int=commands.Param(description=Strings.dt_guild_id_param_description)):
    settings = tracking_settings_repo.get_tracking_settings(inter.guild.id, guild_id)
    guild_name = settings.dt_guild.name

    if tracking_settings_repo.remove_tracking_settings(inter.guild.id, guild_id):
      await message_utils.generate_success_message(inter, Strings.event_data_tracker_remove_tracker_success(guild=guild_name))
    else:
      await message_utils.generate_error_message(inter, Strings.event_data_tracker_remove_tracker_failed(guild_id=guild_id))

  @tracker.sub_command(name="list", description=Strings.event_data_tracker_list_trackers_description)
  @cooldowns.default_cooldown
  async def list_guild_trackers(self, inter: disnake.CommandInteraction):
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

        page.add_field(name=f"{guild_name}({guild_level})", value="No reporting" if announce_channel is None else f"[#{announce_channel.name}]({announce_channel.jump_url})")
      pages.append(page)

    embed_view = EmbedView(inter.author, pages, invisible=True)
    await embed_view.run(inter)

  @tracker.sub_command(description=Strings.event_data_tracker_generate_announcements_description)
  @cooldowns.huge_cooldown
  async def generate_announcements(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    trackers = tracking_settings_repo.get_all_guild_trackers(inter.guild.id)
    if not trackers:
      return await message_utils.generate_error_message(inter, Strings.event_data_tracker_generate_announcements_no_data)

    for tracker in trackers:
      await self.send_tracker_text_announcement(tracker)
      await asyncio.sleep(0.1)

    await message_utils.generate_success_message(inter, Strings.event_data_tracker_generate_announcements_success)

  async def send_tracker_text_announcement(self, tracker: tracking_settings_repo.TrackingSettings):
    announce_channel = await tracker.get_announce_channel(self.bot)
    if announce_channel is None:
      # Announce channel not found so the tracker is not valid anymore
      tracking_settings_repo.session.delete(tracker)
      return

    participations = event_participation_repo.get_recent_guild_event_participations(tracker.dt_guild_id)
    if not participations: return

    await dt_report_generators.send_text_guild_event_participation_report(announce_channel, tracker.dt_guild, participations)

  @tasks.loop(hours=24*7)
  async def result_announce_task(self):
    logger.info("Update before announcement starting")

    guild_ids = tracking_settings_repo.get_tracked_guild_ids()

    if guild_ids is not None:
      for guild_id in guild_ids:
        data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)

        await asyncio.sleep(1)
        if data is None: continue

        event_participation_repo.generate_or_update_event_participations(data)
    logger.info("Update before announcement finished")

    logger.info("Starting Announcement")
    trackers = tracking_settings_repo.get_all_trackers()
    for tracker in trackers:
      await self.send_tracker_text_announcement(tracker)
      await asyncio.sleep(0.25)
    logger.info(f"Announcements send, next announcement {datetime.datetime.utcnow() + datetime.timedelta(days=7)}")

  @result_announce_task.before_loop
  async def result_announce_wait_pretask(self):
    logger.info(f"Current date: {datetime.datetime.utcnow()}")

    today = datetime.datetime.utcnow()
    today_announce_time = datetime.datetime.utcnow().replace(hour=config.event_tracker.announce_time_hours, minute=config.event_tracker.announce_time_minutes, second=0, microsecond=0)
    next_monday = today_announce_time + datetime.timedelta(days=(7 - config.event_tracker.announce_day_index) - (today.weekday() % 7))
    if today.weekday() == 0 and (today.hour < config.event_tracker.announce_time_hours or (today.hour == config.event_tracker.announce_time_hours and today.minute < config.event_tracker.announce_time_minutes)):
      next_monday -= datetime.timedelta(days=7)
    delta_to_next_monday = next_monday - datetime.datetime.utcnow()

    logger.info(f"Next announce date: {next_monday}")
    logger.info(f"Next announcement in {humanize.naturaldelta(delta_to_next_monday)}")
    await asyncio.sleep(delta_to_next_monday.total_seconds())

def setup(bot):
  bot.add_cog(DTEventTracker(bot))
