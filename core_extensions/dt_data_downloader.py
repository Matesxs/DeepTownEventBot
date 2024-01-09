import io
import re
import pandas as pd
import disnake
from disnake.ext import tasks, commands
import asyncio
import datetime
import traceback

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from config import config, Strings, cooldowns
from utils import dt_helpers, command_utils, message_utils, dt_autocomplete
from database import dt_guild_repo, event_participation_repo, dt_blacklist_repo, tracking_settings_repo, dt_guild_member_repo
from database.tables import dt_statistics

logger = setup_custom_logger(__name__)

guild_id_regex = re.compile(r".*_guild_id_(\d+)_.*")

class DTDataDownloader(Base_Cog):
  def __init__(self, bot):
    super(DTDataDownloader, self).__init__(bot, __file__)

  def cog_load(self):
    if config.data_manager.clean_none_existing_guilds:
      if not self.cleanup_task.is_running():
        self.cleanup_task.start()

    if config.data_manager.periodically_pull_data:
      if not self.data_update_task.is_running():
        self.data_update_task.start()

  def cog_unload(self):
    if self.cleanup_task.is_running():
      self.cleanup_task.cancel()

    if self.data_update_task.is_running():
      self.data_update_task.cancel()

    if self.inactive_guild_data_update_task.is_running():
      self.inactive_guild_data_update_task.cancel()

  @command_utils.master_only_slash_command(name="data_update")
  async def data_update_commands(self, inter: disnake.CommandInteraction):
    pass

  @data_update_commands.sub_command(name="guild", description=Strings.data_manager_update_guild_description)
  @cooldowns.default_cooldown
  @commands.is_owner()
  async def update_guild(self, inter: disnake.CommandInteraction,
                         identifier=commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_autocomplete.autocomplete_identifier_guild, converter=dt_autocomplete.guild_user_identifier_converter)):
    await inter.response.defer(with_message=True, ephemeral=True)

    if identifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    guild_id = identifier[1]

    data = await dt_helpers.get_dt_guild_data(guild_id, True)
    if data is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_update_guild_get_failed(identifier=guild_id))

    await event_participation_repo.generate_or_update_event_participations(data)

    await message_utils.generate_success_message(inter, Strings.data_manager_update_guild_success(guild=data.name))

  @data_update_commands.sub_command(name="all_guilds", description=Strings.data_manager_update_all_guilds_description)
  @cooldowns.huge_cooldown
  @commands.is_owner()
  async def update_all_guilds(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    guild_ids = await dt_helpers.get_ids_of_all_guilds()

    last_update = datetime.datetime.utcnow()

    if guild_ids is not None or not guild_ids:
      pulled_data = 0

      for idx, guild_id in enumerate(guild_ids):
        data = await dt_helpers.get_dt_guild_data(guild_id)
        if datetime.datetime.utcnow() - last_update > datetime.timedelta(seconds=10):
          await inter.edit_original_response(f"```\nGuild {idx + 1}/{len(guild_ids)}\n```")
          last_update = datetime.datetime.utcnow()

        await asyncio.sleep(1)
        if data is None: continue

        await event_participation_repo.generate_or_update_event_participations(data)
        pulled_data += 1

      if not inter.is_expired():
        return await message_utils.generate_success_message(inter, Strings.data_manager_update_all_guilds_success_without_periodic_update(guild_num=pulled_data))

      original_message = await inter.original_message()
      if original_message is not None:
        await message_utils.generate_success_message(original_message, Strings.data_manager_update_all_guilds_success_without_periodic_update(guild_num=pulled_data))
      return
    await message_utils.generate_error_message(inter, Strings.data_manager_update_all_guilds_failed_without_periodic_update)

  @data_update_commands.sub_command(name="tracked_guilds", description=Strings.data_manager_update_tracked_guilds_description)
  @cooldowns.huge_cooldown
  @commands.is_owner()
  async def update_tracked_guilds(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    guild_ids = await tracking_settings_repo.get_tracked_guild_ids()

    if guild_ids is not None or not guild_ids:
      pulled_data = 0

      last_update = datetime.datetime.utcnow()

      for idx, guild_id in enumerate(guild_ids):
        data = await dt_helpers.get_dt_guild_data(guild_id, True)
        if datetime.datetime.utcnow() - last_update > datetime.timedelta(seconds=10):
          await inter.edit_original_response(f"```\nGuild {idx + 1}/{len(guild_ids)}\n```")
          last_update = datetime.datetime.utcnow()

        await asyncio.sleep(0.5)
        if data is None: continue

        await event_participation_repo.generate_or_update_event_participations(data)
        pulled_data += 1

      if not inter.is_expired():
        return await message_utils.generate_success_message(inter, Strings.data_manager_update_tracked_guilds_success(guild_num=pulled_data))

      original_message = await inter.original_message()
      if original_message is not None:
        await message_utils.generate_success_message(original_message, Strings.data_manager_update_tracked_guilds_success(guild_num=pulled_data))
      return

    await message_utils.generate_error_message(inter, Strings.data_manager_update_tracked_guilds_failed)

  @command_utils.master_only_message_command(name="Load Event Data")
  @cooldowns.long_cooldown
  @commands.max_concurrency(1, commands.BucketType.default)
  @commands.is_owner()
  async def load_data(self, inter: disnake.MessageCommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    attachments = inter.target.attachments
    if not attachments:
      return await message_utils.generate_error_message(inter, Strings.data_manager_load_data_no_attachments)

    csv_files = []
    for attachment in attachments:
      if attachment.filename.lower().endswith(".csv"):
        csv_files.append(attachment)

    last_sleep = datetime.datetime.utcnow()

    updated_rows = 0
    for file_idx, file in enumerate(csv_files):
      try:
        data = io.BytesIO(await file.read())
        dataframe = pd.read_csv(data, sep=";")
      except:
        continue

      guild_id_results = guild_id_regex.findall(file.filename.lower())
      if len(guild_id_results) != 1 or not str(guild_id_results[0]).isnumeric():
        logger.warning(f"Failed to get guild id from file `{file.filename}`")
        continue

      guild_id = int(guild_id_results[0])

      for row_idx, (_, row) in enumerate(dataframe.iterrows()):
        try:
          user_id = int(row["user_id"])

          if "amount" in row.keys():
            ammount = int(row["amount"])
          elif "donate" in row.keys():
            ammount = int(row["donate"])
          else:
            logger.warning("Donate amount not found")
            break

          if "week" in row.keys() and "year" in row.keys():
            week = int(row["week"])
            year = int(row["year"])
          elif "date" in row.keys():
            try:
              date = datetime.datetime.fromisoformat(row["date"])
              year, week = dt_helpers.get_event_index(date)
            except:
              continue
          elif "timestamp" in row.keys():
            try:
              date = datetime.datetime.fromtimestamp(row["timestamp"])
              year, week = dt_helpers.get_event_index(date)
            except:
              continue
          else:
            logger.warning("Invalid event identifier")
            break

          member = await dt_guild_member_repo.create_dummy_dt_guild_member(user_id, guild_id, year, week, ammount)
          if member is None:
            continue

          if "username" in row.keys():
            member.user.username = row["username"]

          await event_participation_repo.get_and_update_event_participation(user_id, guild_id, year, week, ammount)
          await asyncio.sleep(0.02)

          if datetime.datetime.utcnow() - last_sleep >= datetime.timedelta(seconds=20):
            try:
              await inter.edit_original_response(f"```\nFile {file_idx + 1}/{len(csv_files)}\nData row {row_idx + 1}/{dataframe.shape[0]}\n```")
              logger.info(f"File {file_idx + 1}/{len(csv_files)} Data row {row_idx + 1}/{dataframe.shape[0]}")
            except:
              pass
            last_sleep = datetime.datetime.utcnow()

          updated_rows += 1
        except Exception:
          logger.warning(traceback.format_exc())

    await event_participation_repo.run_commit()

    logger.info(f"Loaded {updated_rows} data rows")

    if not inter.is_expired():
      return await message_utils.generate_success_message(inter, Strings.data_manager_load_data_loaded(count=updated_rows))

    try:
      message = await inter.original_message()

      if message is not None:
        await message_utils.generate_success_message(message, Strings.data_manager_load_data_loaded(count=updated_rows))
    except:
      pass

  @tasks.loop(hours=config.data_manager.cleanup_rate_days * 24)
  async def cleanup_task(self):
    logger.info("Starting cleanup")
    all_guild_ids = await dt_helpers.get_ids_of_all_guilds()
    if all_guild_ids is None:
      logger.error("Failed to get all ids of guilds")
    else:
      removed_guilds = await dt_guild_repo.remove_deleted_guilds(all_guild_ids)
      logger.info(f"Remove {removed_guilds} deleted guilds from database")
    logger.info("Cleanup finished")

  @tasks.loop(hours=config.data_manager.inactive_guild_data_pull_rate_hours)
  async def inactive_guild_data_update_task(self):
    inactive_guild_ids = await dt_guild_repo.get_inactive_guild_ids()

    logger.info("Inactive DT Guild data pull starting")

    if inactive_guild_ids:
      pulled_data = 0

      for idx, guild_id in enumerate(inactive_guild_ids):
        data = await dt_helpers.get_dt_guild_data(guild_id)

        await asyncio.sleep(2)
        if data is None:
          continue

        await event_participation_repo.generate_or_update_event_participations(data)
        pulled_data += 1

      logger.info(f"Pulled data of {pulled_data} inactive DT guilds")
      logger.info(f"New count of active guilds: {await dt_guild_repo.get_number_of_active_guilds()}")

      # Generate new activity statistics
      await dt_statistics.DTActiveEntitiesData.generate()
    logger.info("Inactive DT Guild data pull finished")

  @tasks.loop(hours=max(config.data_manager.data_pull_rate_hours, 1))
  async def data_update_task(self):
    await asyncio.sleep(config.data_manager.pull_data_startup_delay_seconds)

    logger.info("DT Guild data pull starting")
    guild_ids = await dt_helpers.get_ids_of_all_guilds()
    await asyncio.sleep(0.1)

    if guild_ids is not None and guild_ids:
      pulled_data = 0
      not_updated = []

      self.bot.presence_handler.stop()

      last_update = datetime.datetime.utcnow()
      await self.bot.change_presence(activity=disnake.Game(name="Updating data..."), status=disnake.Status.dnd)

      number_of_guilds = len(guild_ids)
      for idx, guild_id in enumerate(guild_ids):
        if datetime.datetime.utcnow() - last_update >= datetime.timedelta(minutes=1):
          progress_percent = (idx / number_of_guilds) * 100
          await self.bot.change_presence(activity=disnake.Game(name=f"Updating data {progress_percent:.1f}%..."), status=disnake.Status.dnd)
          last_update = datetime.datetime.utcnow()

        if (await dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.GUILD, guild_id)) or not (await dt_guild_repo.is_guild_active(guild_id)):
          continue

        data = await dt_helpers.get_dt_guild_data(guild_id)

        await asyncio.sleep(1)
        if data is None:
          not_updated.append(guild_id)
          continue

        await event_participation_repo.generate_or_update_event_participations(data)
        pulled_data += 1

      number_of_not_updated_guilds = len(not_updated)
      if number_of_not_updated_guilds > 0:
        logger.info(f"{number_of_not_updated_guilds} guild not updated, retrying")

        await asyncio.sleep(30)

        last_update = datetime.datetime.utcnow()
        await self.bot.change_presence(activity=disnake.Game(name="Updating data..."), status=disnake.Status.dnd)

        for idx, guild_id in enumerate(not_updated.copy()):
          if datetime.datetime.utcnow() - last_update >= datetime.timedelta(minutes=1):
            progress_percent = (idx / number_of_not_updated_guilds) * 100
            await self.bot.change_presence(activity=disnake.Game(name=f"Updating data {progress_percent:.1f}%..."), status=disnake.Status.dnd)
            last_update = datetime.datetime.utcnow()

          if (await dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.GUILD, guild_id)) or not (await dt_guild_repo.is_guild_active(guild_id)):
            continue

          data = await dt_helpers.get_dt_guild_data(guild_id)

          await asyncio.sleep(1)
          if data is None:
            continue

          not_updated.remove(guild_id)
          await event_participation_repo.generate_or_update_event_participations(data)
          pulled_data += 1

      logger.info(f"Pulled data of {pulled_data} DT guilds\n{not_updated} guilds not updated")

      # Generate new activity statistics
      await dt_statistics.DTActiveEntitiesData.generate()

    logger.info("DT Guild data pull finished")

    await asyncio.sleep(30)
    self.bot.presence_handler.start()

    if not self.inactive_guild_data_update_task.is_running() and config.data_manager.inactive_guild_data_pull_rate_hours > 0:
      self.inactive_guild_data_update_task.start()

def setup(bot):
  bot.add_cog(DTDataDownloader(bot))
