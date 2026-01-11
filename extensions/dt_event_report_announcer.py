import collections
import copy

import disnake
from disnake.ext import commands, tasks
import math
import datetime
import asyncio
from sqlalchemy import exc

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from utils import dt_helpers, dt_report_generators, message_utils, dt_autocomplete, command_utils, object_getters
from database import event_participation_repo, tracking_settings_repo, session_maker
from config import Strings, cooldowns, config, permissions
from features.views.paginator import EmbedView

logger = setup_custom_logger(__name__)

def get_announce_time() -> datetime.time:
  return datetime.time(hour=config.event_tracker.event_start_hour + config.event_tracker.event_length_hours + ((config.event_tracker.event_start_minute + config.event_tracker.event_length_minutes + config.event_tracker.event_announce_offset_minutes) // 60),
                       minute=(config.event_tracker.event_start_minute + config.event_tracker.event_length_minutes + config.event_tracker.event_announce_offset_minutes) % 60, second=0)

class DTEventReportAnnouncer(Base_Cog):
  def __init__(self, bot):
    super(DTEventReportAnnouncer, self).__init__(bot, __file__)

  def cog_load(self):
    if not self.result_announce_task.is_running():
      self.result_announce_task.start()

  def cog_unload(self) -> None:
    if self.result_announce_task.is_running():
      self.result_announce_task.cancel()

  @commands.slash_command(dm_permission=False)
  @permissions.guild_administrator_role()
  async def report_announcer(self, inter: disnake.CommandInteraction):
    pass

  @report_announcer.sub_command(name="modify", description=Strings.event_report_announcer_add_or_modify_tracker_description)
  @cooldowns.default_cooldown
  async def add_or_modify_tracker(self, inter: disnake.CommandInteraction,
                                  identifier=commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_autocomplete.autocomplete_identifier_guild, converter=dt_autocomplete.guild_user_identifier_converter),
                                  text_announce_channel: disnake.TextChannel=commands.Param(description=Strings.discord_text_channel_param_description, default=None),
                                  csv_announce_channel: disnake.TextChannel=commands.Param(description=Strings.discord_text_channel_param_description, default=None)):
    await inter.response.defer(with_message=True, ephemeral=True)

    if identifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    if text_announce_channel is None and csv_announce_channel is None and not (await permissions.is_bot_developer(inter)):
      return await message_utils.generate_error_message(inter, Strings.event_report_announcer_add_or_modify_tracker_no_channels_set)

    if text_announce_channel is not None and not text_announce_channel.permissions_for(inter.guild.me).send_messages:
      return await message_utils.generate_error_message(inter, Strings.discord_cant_send_message_to_channel(channel_name=text_announce_channel.name))

    if csv_announce_channel is not None:
      if not csv_announce_channel.permissions_for(inter.guild.me).send_messages:
        return await message_utils.generate_error_message(inter, Strings.discord_cant_send_message_to_channel(channel_name=csv_announce_channel.name))

      if not csv_announce_channel.permissions_for(inter.guild.me).attach_files:
        return await message_utils.generate_error_message(inter, Strings.discord_cant_send_files_to_channel(channel_name=csv_announce_channel.name))

    with session_maker() as session:
      existing_tracker = await tracking_settings_repo.get_tracking_settings(session, inter.guild.id, identifier[1])
      if not existing_tracker:
        if not (await permissions.is_bot_developer(inter)):
          all_trackers = await tracking_settings_repo.get_all_guild_trackers(session, inter.guild.id)
          if len(all_trackers) >= config.event_tracker.tracker_limit_per_guild:
            return await message_utils.generate_error_message(inter, Strings.event_report_announcer_add_or_modify_tracker_tracker_limit_reached(limit=config.event_report_announcer.tracker_limit_per_guild))

        existing_tracker = await tracking_settings_repo.get_or_create_tracking_settings(session, inter.guild, identifier[1],
                                                                                        text_announce_channel.id if text_announce_channel is not None else None,
                                                                                        csv_announce_channel.id if csv_announce_channel is not None else None)
        if existing_tracker is None:
          return await message_utils.generate_error_message(inter, Strings.dt_guild_not_found(identifier=identifier[1]))
      else:
        existing_tracker.text_announce_channel_id = str(text_announce_channel.id) if text_announce_channel is not None else None
        existing_tracker.csv_announce_channel_id = str(csv_announce_channel.id) if csv_announce_channel is not None else None

      await message_utils.generate_success_message(inter, Strings.event_report_announcer_add_or_modify_tracker_success_with_channel(guild=existing_tracker.dt_guild.name,
                                                                                                                                    channel1=text_announce_channel.name if text_announce_channel is not None else None,
                                                                                                                                    channel2=csv_announce_channel.name if csv_announce_channel is not None else None))
    return None

  @report_announcer.sub_command(name="remove", description=Strings.event_report_announcer_remove_tracker_description)
  @cooldowns.default_cooldown
  async def remove_tracker(self, inter: disnake.CommandInteraction,
                           identifier=commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_autocomplete.autocomplete_identifier_tracked_guild, converter=dt_autocomplete.guild_user_identifier_converter)):
    await inter.response.defer(with_message=True, ephemeral=True)

    if identifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    with session_maker() as session:
      settings = await tracking_settings_repo.get_tracking_settings(session, inter.guild.id, identifier[1])
      if settings is None:
        return await message_utils.generate_error_message(inter, Strings.event_report_announcer_remove_tracker_failed(identifier=identifier[1]))

      guild_name = settings.dt_guild.name

      if await tracking_settings_repo.remove_tracking_settings(session, inter.guild.id, identifier[1]):
        await message_utils.generate_success_message(inter, Strings.event_report_announcer_remove_tracker_success(guild=guild_name))
      else:
        await message_utils.generate_error_message(inter, Strings.event_report_announcer_remove_tracker_failed(identifier=identifier[1]))
      return None

  @report_announcer.sub_command(name="list", description=Strings.event_report_announcer_list_trackers_description)
  @cooldowns.default_cooldown
  async def list_guild_trackers(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    pages = []
    with session_maker() as session:
      guild_trackers = await tracking_settings_repo.get_all_guild_trackers(session, inter.guild.id)

      number_of_trackers = len(guild_trackers)
      if number_of_trackers == 0:
        return await message_utils.generate_error_message(inter, Strings.event_report_announcer_list_trackers_no_trackers)

      num_of_batches = math.ceil(number_of_trackers / 12)
      batches = [guild_trackers[i * 12:i * 12 + 12] for i in range(num_of_batches)]

      for batch in batches:
        page = disnake.Embed(title="Announce list", color=disnake.Color.dark_blue())
        message_utils.add_author_footer(page, inter.author)

        for setting in batch:
          announce_channel = await setting.get_text_announce_channel(self.bot)
          csv_announce_channel = await setting.get_csv_announce_channel(self.bot)
          value_string = "\n".join(["No text reporting" if announce_channel is None else f"Text: [#{announce_channel.name}]({announce_channel.jump_url})",
                                    "No csv reporting" if csv_announce_channel is None else f"CSV: [#{csv_announce_channel.name}]({csv_announce_channel.jump_url})"])

          page.add_field(name=f"{setting.dt_guild.name}({setting.dt_guild_id})", value=value_string)
        pages.append(page)

    embed_view = EmbedView(inter.author, pages, invisible=True)
    await embed_view.run(inter)
    return None

  @command_utils.master_only_slash_command(description=Strings.event_report_announcer_manual_announcement_description)
  @cooldowns.long_cooldown
  @permissions.bot_developer()
  async def manual_announcement(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)
    message = await object_getters.get_or_fetch_message(self.bot, inter.channel, (await inter.original_response()).id)
    await inter.send("Starting announcement...")
    await self.make_announcement()
    await message_utils.generate_success_message(message, Strings.event_report_announcer_manual_announcement_success, replace=True)

  async def make_announcement(self):
    text_announced = []
    csv_announced = []
    full_announced = []
    updated_guilds = []

    logger.info("Starting Announcement")

    year, week = dt_helpers.get_event_index(datetime.datetime.now(datetime.UTC).replace(tzinfo=None))

    while True:
      try:
        with session_maker() as session:
          not_updated_guilds_queue = collections.deque(await tracking_settings_repo.get_tracked_guild_ids(session))

          number_of_failed_updates = 0
          while not_updated_guilds_queue:
            working_copy_of_not_updated_guilds = copy.deepcopy(not_updated_guilds_queue)
            not_updated_guilds_queue.clear()

            while working_copy_of_not_updated_guilds:
              guild_id = working_copy_of_not_updated_guilds.popleft()

              if guild_id in updated_guilds:
                continue

              data = await dt_helpers.get_dt_guild_data(guild_id, True)

              if data is None:
                await asyncio.sleep(20)
                data = await dt_helpers.get_dt_guild_data(guild_id, True)

              await asyncio.sleep(0.5)
              if data is None:
                await asyncio.sleep(20)
                not_updated_guilds_queue.append(guild_id)
                continue

              await event_participation_repo.generate_or_update_event_participations(session, data)
              updated_guilds.append(guild_id)

            if not_updated_guilds_queue:
              if number_of_failed_updates >= 60:
                # Give up after 60 attempts
                logger.warning(f"{list(not_updated_guilds_queue)} guilds not updated for report (already failed {number_of_failed_updates}x), giving up")
                break
              else:
                logger.warning(f"{list(not_updated_guilds_queue)} guilds not updated for report (already failed {number_of_failed_updates}x), retrying")
                number_of_failed_updates += 1
                await asyncio.sleep(120)

          trackers = tracking_settings_repo.get_all_trackers(session)
          async for tracker in trackers:
            if tracker.guild_id in full_announced:
              continue

            text_announce_channel = await tracker.get_text_announce_channel(self.bot)
            csv_announce_channel = await tracker.get_csv_announce_channel(self.bot)
            if text_announce_channel is None and csv_announce_channel is None: continue

            participations = await event_participation_repo.get_event_participations(session, guild_id=int(tracker.dt_guild_id), year=year, week=week, order_by=[event_participation_repo.EventParticipation.amount.desc()])
            if not participations: continue

            if text_announce_channel is not None and text_announce_channel.permissions_for(text_announce_channel.guild.me).send_messages:
              if tracker.guild_id in text_announced:
                continue

              await dt_report_generators.send_text_guild_event_participation_report(text_announce_channel, participations, colm_padding=0)
              text_announced.append(tracker.guild_id)
              await asyncio.sleep(0.1)

            if csv_announce_channel is not None and csv_announce_channel.permissions_for(csv_announce_channel.guild.me).send_messages and csv_announce_channel.permissions_for(csv_announce_channel.guild.me).attach_files:
              if tracker.guild_id in csv_announced:
                continue

              await dt_report_generators.send_csv_guild_event_participation_report(csv_announce_channel, tracker.dt_guild, participations)
              csv_announced.append(tracker.guild_id)
              await asyncio.sleep(0.1)

            full_announced.append(tracker.guild_id)

        break
      except exc.OperationalError as e:
        if e.connection_invalidated:
          logger.warning("Database connection failed, retrying later")
          await asyncio.sleep(60)
          logger.info("Retrying...")
        else:
          raise e

    logger.info("Announcements send")

  @tasks.loop(time=get_announce_time())
  async def result_announce_task(self):
    await self.bot.wait_until_ready()

    current_datetime = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)
    previous_week_date = current_datetime - datetime.timedelta(days=7)
    prev_year, prev_week = dt_helpers.get_event_index(previous_week_date)
    _, prev_event_end = dt_helpers.event_index_to_date_range(prev_year, prev_week)

    if prev_event_end.weekday() == current_datetime.weekday():
      await self.make_announcement()

def setup(bot):
  bot.add_cog(DTEventReportAnnouncer(bot))
