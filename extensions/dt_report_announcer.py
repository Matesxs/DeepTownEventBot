import disnake
from disnake.ext import commands, tasks
import math
import datetime
import asyncio
import humanize

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from utils import dt_helpers, dt_report_generators, message_utils, dt_identifier_autocomplete
from database import event_participation_repo, tracking_settings_repo
from config import Strings, cooldowns, config, permissions
from features.views.paginator import EmbedView

logger = setup_custom_logger(__name__)

class DTEventReportAnnouncer(Base_Cog):
  def __init__(self, bot):
    super(DTEventReportAnnouncer, self).__init__(bot, __file__)
    if not self.result_announce_task.is_running():
      self.result_announce_task.start()

  def cog_unload(self) -> None:
    if self.result_announce_task.is_running():
      self.result_announce_task.cancel()

  @commands.slash_command()
  @permisions.guild_owner()
  @commands.guild_only()
  async def announcer(self, inter: disnake.CommandInteraction):
    pass

  @announcer.sub_command(name="modify", description=Strings.event_report_announcer_add_or_modify_tracker_description)
  @cooldowns.default_cooldown
  async def add_or_modify_tracker(self, inter: disnake.CommandInteraction,
                                  identifier: str=commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_identifier_autocomplete.autocomplete_identifier_guild),
                                  announce_channel: disnake.TextChannel=commands.Param(description=Strings.discord_text_channel_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    specifier = dt_identifier_autocomplete.identifier_to_specifier(identifier)
    if specifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    existing_tracker = tracking_settings_repo.get_tracking_settings(inter.guild.id, specifier[1])
    if not existing_tracker:
      if self.bot.owner is None or inter.author.id != self.bot.owner.id:
        all_trackers = tracking_settings_repo.get_all_guild_trackers(inter.guild.id)
        if len(all_trackers) >= config.event_tracker.tracker_limit_per_guild:
          return await message_utils.generate_error_message(inter, Strings.event_report_announcer_add_or_modify_tracker_tracker_limit_reached(limit=config.event_report_announcer.tracker_limit_per_guild))

      existing_tracker = tracking_settings_repo.get_or_create_tracking_settings(inter.guild, specifier[1], announce_channel.id)
      if existing_tracker is None:
        return await message_utils.generate_error_message(inter, Strings.dt_guild_not_found(identifier=identifier))
    else:
      existing_tracker.announce_channel_id = str(announce_channel.id)
      tracking_settings_repo.session.commit()

    await message_utils.generate_success_message(inter, Strings.event_report_announcer_add_or_modify_tracker_success_with_channel(guild=existing_tracker.dt_guild.name, channel=announce_channel.name))

  @announcer.sub_command(name="remove", description=Strings.event_report_announcer_remove_tracker_description)
  @cooldowns.default_cooldown
  async def remove_tracker(self, inter: disnake.CommandInteraction,
                                 identifier: str=commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_identifier_autocomplete.autocomplete_identifier_guild)):
    specifier = dt_identifier_autocomplete.identifier_to_specifier(identifier)
    if specifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    settings = tracking_settings_repo.get_tracking_settings(inter.guild.id, specifier[1])
    if settings is None:
      return await message_utils.generate_error_message(inter, Strings.event_report_announcer_remove_tracker_failed(identifier=specifier[1]))

    guild_name = settings.dt_guild.name

    if tracking_settings_repo.remove_tracking_settings(inter.guild.id, specifier[1]):
      await message_utils.generate_success_message(inter, Strings.event_report_announcer_remove_tracker_success(guild=guild_name))
    else:
      await message_utils.generate_error_message(inter, Strings.event_report_announcer_remove_tracker_failed(identifier=specifier[1]))

  @announcer.sub_command(name="list", description=Strings.event_report_announcer_list_trackers_description)
  @cooldowns.default_cooldown
  async def list_guild_trackers(self, inter: disnake.CommandInteraction):
    guild_trackers = tracking_settings_repo.get_all_guild_trackers(inter.guild.id)
    number_of_trackers = len(guild_trackers)

    if number_of_trackers == 0:
      return await message_utils.generate_error_message(inter, Strings.event_report_announcer_list_trackers_no_trackers)

    num_of_batches = math.ceil(number_of_trackers / 12)
    batches = [guild_trackers[i * 12:i * 12 + 12] for i in range(num_of_batches)]

    pages = []
    for batch in batches:
      page = disnake.Embed(title="Announce list", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(page, inter.author)

      for setting in batch:
        guild_name = setting.dt_guild.name
        guild_level = setting.dt_guild.level
        announce_channel = await setting.get_announce_channel(self.bot)

        page.add_field(name=f"{guild_name}({guild_level})", value="No reporting" if announce_channel is None else f"[#{announce_channel.name}]({announce_channel.jump_url})")
      pages.append(page)

    embed_view = EmbedView(inter.author, pages, invisible=True)
    await embed_view.run(inter)

  @tasks.loop(hours=24*7)
  async def result_announce_task(self):
    logger.info("Update before announcement starting")

    guild_ids = tracking_settings_repo.get_tracked_guild_ids()

    if guild_ids is not None:
      for guild_id in guild_ids:
        data = await dt_helpers.get_dt_guild_data(guild_id, True)

        await asyncio.sleep(1)
        if data is None: continue

        event_participation_repo.generate_or_update_event_participations(data)
    logger.info("Update before announcement finished")

    year, week = dt_helpers.get_event_index(datetime.datetime.utcnow())

    logger.info("Starting Announcement")
    trackers = tracking_settings_repo.get_all_trackers()
    for tracker in trackers:
      announce_channel = await tracker.get_announce_channel(self.bot)
      if announce_channel is None:
        # Announce channel not found so the tracker is not valid anymore
        tracking_settings_repo.session.delete(tracker)
        continue

      participations = event_participation_repo.get_event_participations(guild_id=int(tracker.dt_guild_id), year=year, week=week, order_by=[event_participation_repo.EventParticipation.amount.desc()])
      if not participations: continue

      await dt_report_generators.send_text_guild_event_participation_report(announce_channel, tracker.dt_guild, participations, colm_padding=0)
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
  bot.add_cog(DTEventReportAnnouncer(bot))
