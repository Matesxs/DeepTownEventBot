import datetime
import disnake
from disnake.ext import commands, tasks
from typing import Optional
import asyncio
import pandas as pd
import io
import traceback

from features.base_cog import Base_Cog
from utils import dt_helpers, message_utils
from utils.logger import setup_custom_logger
from config import cooldowns, Strings, config
from database import event_participation_repo, tracking_settings_repo, dt_guild_repo, dt_guild_member_repo

logger = setup_custom_logger(__name__)

class DTDataManager(Base_Cog):
  def __init__(self, bot):
    super(DTDataManager, self).__init__(bot, __file__)

    self.data_loading = False

    if config.data_manager.clean_none_existing_guilds:
      if not self.cleanup_task.is_running():
        self.cleanup_task.start()

    self.skip_periodic_data_update = True
    if config.data_manager.periodically_pull_data:
      if not self.data_update_task.is_running():
        self.data_update_task.start()

    self.all_item_names = event_participation_repo.get_all_dt_item_names()

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
  async def update_guild(self, inter: disnake.CommandInteraction, identifier: str=commands.Param(description=Strings.dt_guild_identifier_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    if identifier.isnumeric():
      data = await dt_helpers.get_dt_guild_data(self.bot, int(identifier))
      if data is None:
        return await message_utils.generate_error_message(inter, Strings.data_manager_update_guild_get_failed(identifier=identifier))

      event_participation_repo.generate_or_update_event_participations(data)

      await message_utils.generate_success_message(inter, Strings.data_manager_update_guild_success(guild=data.name))
    else:
      matched_guilds = await dt_helpers.get_guild_info(self.bot, identifier)
      if matched_guilds is None or not matched_guilds:
        return await message_utils.generate_error_message(inter, Strings.data_manager_update_guild_get_failed(identifier=identifier))

      guild_ids = [d[0] for d in matched_guilds]
      updated_guilds = 0
      for guild_id in guild_ids:
        data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
        if data is None: continue

        updated_guilds += 1
        event_participation_repo.generate_or_update_event_participations(data)

      await message_utils.generate_success_message(inter, Strings.data_manager_update_guild_success_multiple(number=updated_guilds))

  @data_manager.sub_command(description=Strings.data_manager_update_all_guilds_description)
  @cooldowns.long_cooldown
  @commands.is_owner()
  async def update_all_guilds(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    if config.data_manager.periodically_pull_data:
      self.data_update_task.restart()

      await message_utils.generate_success_message(inter, Strings.data_manager_update_all_guilds_success_with_periodic_update)
    else:
      guild_ids = await dt_helpers.get_ids_of_all_guilds(self.bot)

      last_update = datetime.datetime.utcnow()

      if guild_ids is not None or not guild_ids:
        pulled_data = 0

        for idx, guild_id in enumerate(guild_ids):
          data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
          if datetime.datetime.utcnow() - last_update > datetime.timedelta(seconds=10):
            await inter.edit_original_response(f"```\nGuild {idx+1}/{len(guild_ids)}\n```")
            last_update = datetime.datetime.utcnow()

          await asyncio.sleep(0.2)
          if data is None: continue

          event_participation_repo.generate_or_update_event_participations(data)
          pulled_data += 1

        if not inter.is_expired():
          return await message_utils.generate_success_message(inter, Strings.data_manager_update_all_guilds_success_without_periodic_update(guild_num=pulled_data))

        original_message = await inter.original_message()
        if original_message is not None:
          await message_utils.generate_success_message(original_message, Strings.data_manager_update_all_guilds_success_without_periodic_update(guild_num=pulled_data))
        return
      await message_utils.generate_error_message(inter, Strings.data_manager_update_all_guilds_failed_without_periodic_update)

  @data_manager.sub_command(description=Strings.data_manager_update_tracked_guilds_description)
  @cooldowns.long_cooldown
  @commands.is_owner()
  async def update_tracked_guilds(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    guild_ids = tracking_settings_repo.get_tracked_guild_ids()

    if guild_ids is not None or not guild_ids:
      pulled_data = 0

      last_update = datetime.datetime.utcnow()

      for idx, guild_id in enumerate(guild_ids):
        data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)
        if datetime.datetime.utcnow() - last_update > datetime.timedelta(seconds=10):
          await inter.edit_original_response(f"```\nGuild {idx + 1}/{len(guild_ids)}\n```")
          last_update = datetime.datetime.utcnow()

        await asyncio.sleep(0.2)
        if data is None: continue

        event_participation_repo.generate_or_update_event_participations(data)
        pulled_data += 1

      if not inter.is_expired():
        return await message_utils.generate_success_message(inter, Strings.data_manager_update_tracked_guilds_success(guild_num=pulled_data))

      original_message = await inter.original_message()
      if original_message is not None:
        await message_utils.generate_success_message(original_message, Strings.data_manager_update_tracked_guilds_success(guild_num=pulled_data))
      return

    await message_utils.generate_error_message(inter, Strings.data_manager_update_tracked_guilds_failed)

  @data_manager.sub_command(description=Strings.data_manager_skip_data_update_description)
  @cooldowns.long_cooldown
  @commands.is_owner()
  async def skip_data_update(self, inter: disnake.CommandInteraction):
    if not self.skip_periodic_data_update:
      self.skip_periodic_data_update = True
      await message_utils.generate_success_message(inter, Strings.data_manager_skip_data_update_success)
    else:
      await message_utils.generate_error_message(inter, Strings.data_manager_skip_data_update_failed)

  @data_manager.sub_command(description=Strings.data_manager_dump_guild_participation_data_description)
  @cooldowns.huge_cooldown
  async def dump_guild_participation_data(self, inter: disnake.CommandInteraction, guild_id: Optional[int]=commands.Param(default=None, description=Strings.dt_guild_id_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    dump_data = event_participation_repo.dump_guild_event_participation_data(guild_id)
    if not dump_data:
      if guild_id is not None:
        return await message_utils.generate_error_message(inter, Strings.data_manager_dump_guild_participation_data_no_data(guild_id=guild_id))
      else:
        return await message_utils.generate_error_message(inter, Strings.data_manager_dump_guild_participation_data_no_data_no_guild_id)

    dataframe = pd.DataFrame(dump_data, columns=["year", "week", "guild_id", "guild_name", "user_id", "username", "amount"], index=None)

    data = io.BytesIO()
    dataframe.to_csv(data, sep=";", index=False)

    data.seek(0)
    discord_file = disnake.File(data, filename="guild_dump.csv")

    await message_utils.generate_success_message(inter, Strings.data_manager_dump_guild_participation_data_success)
    await inter.send(file=discord_file)

  @data_manager.sub_command(description=Strings.data_manager_add_dt_item_description)
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def add_dt_item(self, inter: disnake.CommandInteraction,
                        name: str=commands.Param(description=Strings.data_manager_add_remove_dt_item_name_param_description),
                        value: float=commands.Param(default=0.0, description=Strings.data_manager_add_dt_item_value_param_description, min_value=0.0)):
    await inter.response.defer(with_message=True, ephemeral=True)
    event_participation_repo.set_dt_item(name, value)
    self.all_item_names = event_participation_repo.get_all_dt_item_names()
    await message_utils.generate_success_message(inter, Strings.data_manager_add_dt_item_success(name=name, value=value))

  @data_manager.sub_command(description=Strings.data_manager_remove_dt_item_description)
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def remove_dt_item(self, inter: disnake.CommandInteraction,
                           name: str=commands.Param(description=Strings.data_manager_add_remove_dt_item_name_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)
    if event_participation_repo.remove_dt_item(name):
      self.all_item_names = event_participation_repo.get_all_dt_item_names()
      await message_utils.generate_success_message(inter, Strings.data_manager_remove_dt_item_success(name=name))
    else:
      await message_utils.generate_error_message(inter, Strings.data_manager_remove_dt_item_failed(name=name))

  @data_manager.sub_command(description="Set Deep Town items in event")
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def set_event_items(self, inter: disnake.CommandInteraction,
                            event_year: Optional[int]=commands.Param(default=None, min_value=0, description="Event year"),
                            event_week: Optional[int]=commands.Param(default=None, min_value=0, description="Event week"),
                            item1: str=commands.Param(description="Event Deep Town Item 1"),
                            item2: str=commands.Param(description="Event Deep Town Item 2"),
                            item3: str=commands.Param(description="Event Deep Town Item 3"),
                            item4: str=commands.Param(description="Event Deep Town Item 4"),
                            base_amount1: int=commands.Param(default=0, min_value=0, description="Base amount for item 1"),
                            base_amount2: int=commands.Param(default=0, min_value=0, description="Base amount for item 2"),
                            base_amount3: int=commands.Param(default=0, min_value=0, description="Base amount for item 3"),
                            base_amount4: int=commands.Param(default=0, min_value=0, description="Base amount for item 4")):
    await inter.response.defer(with_message=True, ephemeral=True)

    if event_year is None or event_week is None:
      event_year, event_week = dt_helpers.get_event_index(datetime.datetime.utcnow())

    if event_participation_repo.get_dt_item(item1) is None:
      return await message_utils.generate_error_message(inter, f"Item `{item1}` not found in database")

    if event_participation_repo.get_dt_item(item2) is None:
      return await message_utils.generate_error_message(inter, f"Item `{item2}` not found in database")

    if event_participation_repo.get_dt_item(item3) is None:
      return await message_utils.generate_error_message(inter, f"Item `{item3}` not found in database")

    if event_participation_repo.get_dt_item(item4) is None:
      return await message_utils.generate_error_message(inter, f"Item `{item4}` not found in database")

    event_participation_repo.set_event_item(event_year, event_week, item1, base_amount1, commit=False)
    event_participation_repo.set_event_item(event_year, event_week, item2, base_amount2, commit=False)
    event_participation_repo.set_event_item(event_year, event_week, item3, base_amount3, commit=False)
    event_participation_repo.set_event_item(event_year, event_week, item4, base_amount4, commit=False)
    event_participation_repo.session.commit()

    await message_utils.generate_success_message(inter, f"Items for event `{event_year} {event_week}` set\n{item1} - {base_amount1}\n{item2} - {base_amount2}\n{item3} - {base_amount3}\n{item4} - {base_amount4}")

  @data_manager.sub_command(description="Remove Deep Town items for event")
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def remove_event_items(self, inter: disnake.CommandInteraction,
                               event_year: Optional[int]=commands.Param(default=None, min_value=0, description="Event year"),
                               event_week: Optional[int]=commands.Param(default=None, min_value=0, description="Event week")):
    await inter.response.defer(with_message=True, ephemeral=True)

    if event_year is None or event_week is None:
      event_year, event_week = dt_helpers.get_event_index(datetime.datetime.utcnow())

    if event_participation_repo.remove_event_participation_items(event_year, event_week):
      await message_utils.generate_success_message(inter, f"Removed event items for `{event_year} {event_week}`")
    else:
      await message_utils.generate_error_message(inter, f"Can't find event items for `{event_year} {event_week}`")

  @set_event_items.autocomplete("item1")
  @set_event_items.autocomplete("item2")
  @set_event_items.autocomplete("item3")
  @set_event_items.autocomplete("item4")
  @remove_dt_item.autocomplete("name")
  async def autocomplete_item(self, _, string: str):
    if string is None or not string: return self.all_item_names[:25]
    return [item for item in self.all_item_names if string.lower() in item.lower()][:25]

  @commands.message_command(name="Load Event Data")
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
    self.data_loading = True

    updated_rows = 0
    for file_idx, file in enumerate(csv_files):
      data = io.BytesIO(await file.read())
      dataframe = pd.read_csv(data, sep=";")

      for row_idx, (_, row) in enumerate(dataframe.iterrows()):
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
          await asyncio.sleep(0.01)

          if datetime.datetime.utcnow() - last_sleep >= datetime.timedelta(seconds=20):
            try:
              await inter.edit_original_response(f"```\nFile {file_idx + 1}/{len(csv_files)}\nData row {row_idx + 1}/{dataframe.shape[0]}\n```")
            except:
              pass
            last_sleep = datetime.datetime.utcnow()

          updated_rows += 1
        except Exception:
          logger.warning(traceback.format_exc())

    event_participation_repo.session.commit()

    logger.info(f"Loaded {updated_rows} data rows")
    self.data_loading = False

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

    if self.skip_periodic_data_update or self.data_loading:
      logger.info("Data pull interrupted")
      return

    logger.info("Guild data pull starting")
    guild_ids = await dt_helpers.get_ids_of_all_guilds(self.bot)

    if guild_ids is not None or not guild_ids:
      pulled_data = 0
      not_updated = []

      last_update = datetime.datetime.utcnow()
      await self.bot.change_presence(activity=disnake.Game(name="Updating data..."), status=disnake.Status.dnd)

      number_of_guilds = len(guild_ids)
      for idx, guild_id in enumerate(guild_ids):
        if datetime.datetime.utcnow() - last_update >= datetime.timedelta(minutes=1):
          progress_percent = (idx / number_of_guilds) * 100
          await self.bot.change_presence(activity=disnake.Game(name=f"Updating data {progress_percent:.1f}%..."), status=disnake.Status.dnd)
          last_update = datetime.datetime.utcnow()

        if self.skip_periodic_data_update or self.data_loading:
          logger.info("Data pull interrupted")
          break

        data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)

        await asyncio.sleep(1)
        if data is None:
          not_updated.append(guild_id)
          continue

        event_participation_repo.generate_or_update_event_participations(data)
        pulled_data += 1

      number_of_not_updated_guilds = len(not_updated)
      if number_of_not_updated_guilds > 0 and not self.skip_periodic_data_update:
        logger.info(f"{number_of_not_updated_guilds} guild not updated, retrying")

        await asyncio.sleep(30)

        last_update = datetime.datetime.utcnow()
        await self.bot.change_presence(activity=disnake.Game(name="Updating data..."), status=disnake.Status.dnd)

        for idx, guild_id in enumerate(not_updated.copy()):
          if datetime.datetime.utcnow() - last_update >= datetime.timedelta(minutes=1):
            progress_percent = (idx / number_of_not_updated_guilds) * 100
            await self.bot.change_presence(activity=disnake.Game(name=f"Updating data {progress_percent:.1f}%..."), status=disnake.Status.dnd)
            last_update = datetime.datetime.utcnow()

          if self.skip_periodic_data_update or self.data_loading:
            logger.info("Data pull interrupted")
            break

          data = await dt_helpers.get_dt_guild_data(self.bot, guild_id)

          await asyncio.sleep(1)
          if data is None:
            continue

          not_updated.remove(guild_id)
          event_participation_repo.generate_or_update_event_participations(data)
          pulled_data += 1

      logger.info(f"Pulled data of {pulled_data} guilds\nGuilds {not_updated} not updated")
      self.skip_periodic_data_update = True
    logger.info("Guild data pull finished")

    await asyncio.sleep(30)
    await self.bot.change_presence(activity=disnake.Game(name=config.base.status_message), status=disnake.Status.online)

def setup(bot):
  bot.add_cog(DTDataManager(bot))
