import disnake
from disnake.ext import commands, tasks
import asyncio
import pandas as pd
import io
import traceback

from features.base_cog import Base_Cog
from utils import dt_helpers, message_utils, permission_helper
from utils.logger import setup_custom_logger
from config import cooldowns, Strings, config
from database import event_participation_repo, tracking_settings_repo, dt_guild_repo, dt_guild_member_repo

logger = setup_custom_logger(__name__)

class DTDataManager(Base_Cog):
  def __init__(self, bot):
    super(DTDataManager, self).__init__(bot, __file__)
    if config.data_manager.clean_none_existing_guilds:
      if not self.cleanup_task.is_running():
        self.cleanup_task.start()

    self.skip_periodic_data_update = True
    if config.data_manager.periodically_pull_data:
      if not self.data_update_task.is_running():
        self.data_update_task.start()

  def cog_unload(self):
    if self.cleanup_task.is_running():
      self.cleanup_task.cancel()

    if self.data_update_task.is_running():
      self.data_update_task.cancel()

  @commands.slash_command()
  async def data_manager(self, inter: disnake.CommandInteraction):
    pass

  @data_manager.sub_command(description=Strings.data_manager_update_guild_description)
  @cooldowns.long_cooldown
  @commands.is_owner()
  async def update_guild(self, inter: disnake.CommandInteraction, guild_id: int=commands.Param(description="Deep Town Guild ID")):
    await inter.response.defer(with_message=True, ephemeral=True)

    data = event_participation_repo.get_recent_event_participations(guild_id)

    if not data:
      data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
      if data is None:
        return await message_utils.generate_error_message(inter, Strings.data_manager_update_guild_get_failed)

    event_participation_repo.generate_or_update_event_participations(data)

    await message_utils.generate_success_message(inter, Strings.data_manager_update_guild_success(guild=data.name))

  @data_manager.sub_command(description=Strings.data_manager_update_all_guilds_description)
  @cooldowns.long_cooldown
  @commands.is_owner()
  async def update_all_guilds(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    guild_ids = await dt_helpers.get_ids_of_all_guilds(self.bot)

    if guild_ids is not None or not guild_ids:
      pulled_data = 0

      for guild_id in guild_ids:
        data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
        await asyncio.sleep(0.2)
        if data is None: continue

        event_participation_repo.generate_or_update_event_participations(data)
        pulled_data += 1

      return await message_utils.generate_success_message(inter, Strings.data_manager_update_all_guilds_success(guild_num=pulled_data))
    await message_utils.generate_error_message(inter, Strings.data_manager_update_all_guilds_failed)

  @data_manager.sub_command(description=Strings.data_manager_update_tracked_guilds_description)
  @cooldowns.long_cooldown
  @commands.is_owner()
  async def update_tracked_guilds(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    guild_ids = tracking_settings_repo.get_tracked_guild_ids()

    if guild_ids is not None or not guild_ids:
      pulled_data = 0

      for guild_id in guild_ids:
        data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
        await asyncio.sleep(0.2)
        if data is None: continue

        event_participation_repo.generate_or_update_event_participations(data)
        pulled_data += 1

      return await message_utils.generate_success_message(inter, Strings.data_manager_update_tracked_guilds_success(guild_num=pulled_data))
    await message_utils.generate_error_message(inter, Strings.data_manager_update_tracked_guilds_failed)

  @data_manager.sub_command(description=Strings.data_manager_skip_data_update_description)
  @cooldowns.long_cooldown
  @commands.is_owner()
  async def skip_data_update(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    if not self.skip_periodic_data_update:
      self.skip_periodic_data_update = True
      await message_utils.generate_success_message(inter, Strings.data_manager_skip_data_update_success)
    else:
      await message_utils.generate_error_message(inter, Strings.data_manager_skip_data_update_failed)

  @data_manager.sub_command(description=Strings.data_manager_dump_guild_participation_data_description)
  @cooldowns.huge_cooldown
  async def dump_guild_participation_data(self, inter: disnake.CommandInteraction, guild_id: int=commands.Param(description="Deep Town Guild ID")):
    await inter.response.defer(with_message=True, ephemeral=True)

    dump_data = event_participation_repo.dump_guild_event_participation_data(guild_id)
    if not dump_data:
      return await message_utils.generate_error_message(inter, Strings.data_manager_dump_guild_participation_data_no_data(guild_id=guild_id))

    dataframe = pd.DataFrame(dump_data, columns=["year", "week", "guild_id", "guild_name", "user_id", "username", "amount"], index=None)

    data = io.BytesIO()
    dataframe.to_csv(data, sep=";", index=False)

    data.seek(0)
    discord_file = disnake.File(data, filename="guild_dump.csv")

    await message_utils.generate_success_message(inter, Strings.data_manager_dump_guild_participation_data_success)
    await inter.send(file=discord_file)


  @commands.message_command(name="Load Event Data")
  @cooldowns.long_cooldown
  @commands.is_owner()
  async def load_data(self, inter: disnake.MessageCommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    attachments = inter.target.attachments

    csv_files = []
    for attachment in attachments:
      if attachment.filename.lower().endswith(".csv"):
        csv_files.append(attachment)

    updated_rows = 0
    for file in csv_files:
      data = io.BytesIO(await file.read())
      dataframe = pd.read_csv(data, sep=";")

      for index, row in dataframe.iterrows():
        try:
          user_id = int(row["user_id"])
          guild_id = int(row["guild_id"])
          ammount = int(row["amount"])
          week = int(row["week"])
          year = int(row["year"])

          member = dt_guild_member_repo.create_dummy_dt_guild_member(user_id, guild_id)
          if "username" in row.keys():
            member.user.username = row["username"]
          if "guild_name" in row.keys():
            member.guild.name = row["guild_name"]
          event_participation_repo.get_and_update_event_participation(user_id, guild_id, year, week, ammount)
          updated_rows += 1
        except Exception:
          logger.warning(traceback.format_exc())

    event_participation_repo.session.commit()

    await message_utils.generate_success_message(inter, Strings.data_manager_load_data_loaded(count=updated_rows))

  @tasks.loop(hours=config.data_manager.cleanup_rate_days * 24)
  async def cleanup_task(self):
    logger.info("Starting cleanup")
    all_guild_ids = await dt_helpers.get_ids_of_all_guilds(self.bot)
    if all_guild_ids is None:
      logger.error("Failed to get all ids of guilds")
    else:
      removed_guilds = dt_guild_repo.remove_deleted_guilds(all_guild_ids)
      logger.info(f"Remove {removed_guilds} deleted guilds from database")
    logger.info("Cleanup finished")

  @tasks.loop(hours=config.data_manager.data_pull_rate_hours)
  async def data_update_task(self):
    self.skip_periodic_data_update = False
    await asyncio.sleep(config.data_manager.pull_data_startup_delay_seconds)

    if self.skip_periodic_data_update:
      logger.info("Data pull interrupted")
      return

    logger.info("Guild data pull starting")
    if not config.data_manager.monitor_all_guilds:
      guild_ids = tracking_settings_repo.get_tracked_guild_ids()
    else:
      guild_ids = await dt_helpers.get_ids_of_all_guilds(self.bot)

    if guild_ids is not None or not guild_ids:
      pulled_data = 0
      not_updated = []

      for guild_id in guild_ids:
        if self.skip_periodic_data_update:
          logger.info("Data pull interrupted")
          break

        data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)

        await asyncio.sleep(1)
        if data is None:
          not_updated.append(guild_id)
          continue

        event_participation_repo.generate_or_update_event_participations(data)
        pulled_data += 1

      logger.info(f"Pulled data of {pulled_data} guilds\nGuilds {not_updated} not updated")
      self.skip_periodic_data_update = True
    logger.info("Guild data pull finished")

def setup(bot):
  bot.add_cog(DTDataManager(bot))
