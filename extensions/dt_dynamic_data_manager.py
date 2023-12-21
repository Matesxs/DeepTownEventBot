import datetime
import disnake
from disnake.ext import commands
from typing import Optional
import asyncio
import pandas as pd
import io
import traceback
import math
import re

from features.base_cog import Base_Cog
from utils import dt_helpers, message_utils, dt_autocomplete, items_lottery, command_utils
from utils.logger import setup_custom_logger
from config import cooldowns, Strings, permissions
from database import event_participation_repo, tracking_settings_repo, dt_guild_member_repo, dt_items_repo

logger = setup_custom_logger(__name__)

guild_id_regex = re.compile(r".*_guild_id_(\d+)_.*")

class DTDynamicDataManager(Base_Cog):
  def __init__(self, bot):
    super(DTDynamicDataManager, self).__init__(bot, __file__)

  @command_utils.master_only_slash_command()
  async def data_manager(self, inter: disnake.CommandInteraction):
    pass

  @data_manager.sub_command(description=Strings.data_manager_update_guild_description)
  @cooldowns.huge_cooldown
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

  @data_manager.sub_command(description=Strings.data_manager_update_all_guilds_description)
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

  @data_manager.sub_command(description=Strings.data_manager_update_tracked_guilds_description)
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

  @data_manager.sub_command(description=Strings.data_manager_set_event_items_description)
  @cooldowns.short_cooldown
  @permissions.bot_developer()
  async def set_event_items(self, inter: disnake.CommandInteraction,
                            item1: str=commands.Param(description=Strings.data_manager_set_event_items_item_name_param_description(number=1), autocomplete=dt_autocomplete.autocomplete_item),
                            item2: str=commands.Param(description=Strings.data_manager_set_event_items_item_name_param_description(number=2), autocomplete=dt_autocomplete.autocomplete_item),
                            item3: str=commands.Param(description=Strings.data_manager_set_event_items_item_name_param_description(number=3), autocomplete=dt_autocomplete.autocomplete_item),
                            item4: str=commands.Param(description=Strings.data_manager_set_event_items_item_name_param_description(number=4), autocomplete=dt_autocomplete.autocomplete_item),
                            base_amount1: Optional[int]=commands.Param(default=None, min_value=0, description=Strings.data_manager_set_event_items_item_amount_param_description(number=1)),
                            base_amount2: Optional[int]=commands.Param(default=None, min_value=0, description=Strings.data_manager_set_event_items_item_amount_param_description(number=2)),
                            base_amount3: Optional[int]=commands.Param(default=None, min_value=0, description=Strings.data_manager_set_event_items_item_amount_param_description(number=3)),
                            base_amount4: Optional[int]=commands.Param(default=None, min_value=0, description=Strings.data_manager_set_event_items_item_amount_param_description(number=4)),
                            current_level: int = commands.Param(default=0, min_value=0, description=Strings.data_manager_set_event_items_current_level_param_description),
                            update_items_lotteries: bool = commands.Param(default=True, description=Strings.data_manager_set_event_items_update_items_lotteries_param_description),
                            event_identifier=commands.Param(default=None, description=Strings.dt_event_identifier_param_description, autocomplete=dt_autocomplete.autocomplete_event_identifier, converter=dt_autocomplete.event_identifier_converter, convert_defaults=True)):
    await inter.response.defer(with_message=True, ephemeral=True)

    if (await dt_items_repo.get_dt_item(item1)) is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_item_not_in_database(item=item1))

    if (await dt_items_repo.get_dt_item(item2)) is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_item_not_in_database(item=item2))

    if (await dt_items_repo.get_dt_item(item3)) is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_item_not_in_database(item=item3))

    if (await dt_items_repo.get_dt_item(item4)) is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_item_not_in_database(item=item4))

    if len(list(set(list([item1, item2, item3, item4])))) != 4:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_repeated_items)

    await dt_items_repo.remove_event_participation_items(event_identifier[0], event_identifier[1])
    await asyncio.sleep(0.01)

    if current_level != 0:
      base_amount1 = math.ceil(base_amount1 / (0.9202166811 * math.exp((current_level + 1) / 8)))
      base_amount2 = math.ceil(base_amount2 / (0.9202166811 * math.exp((current_level + 1) / 8)))
      base_amount3 = math.ceil(base_amount3 / (0.9202166811 * math.exp((current_level + 1) / 8)))
      base_amount4 = math.ceil(base_amount4 / (0.9202166811 * math.exp((current_level + 1) / 8)))

    futures = [dt_items_repo.set_event_item(event_identifier[0], event_identifier[1], item1, base_amount1, commit=False),
               dt_items_repo.set_event_item(event_identifier[0], event_identifier[1], item2, base_amount2, commit=False),
               dt_items_repo.set_event_item(event_identifier[0], event_identifier[1], item3, base_amount3, commit=False),
               dt_items_repo.set_event_item(event_identifier[0], event_identifier[1], item4, base_amount4, commit=False)]
    await asyncio.gather(*futures)
    await dt_items_repo.run_commit()

    await message_utils.generate_success_message(inter, Strings.data_manager_set_event_items_success(event_year=event_identifier[0],
                                                                                                     event_week=event_identifier[1],
                                                                                                     item1=item1,
                                                                                                     item2=item2,
                                                                                                     item3=item3,
                                                                                                     item4=item4,
                                                                                                     base_amount1=base_amount1,
                                                                                                     base_amount2=base_amount2,
                                                                                                     base_amount3=base_amount3,
                                                                                                     base_amount4=base_amount4))

    if update_items_lotteries:
      result = await items_lottery.process_loterries(self.bot)
      if result is None:
        return await message_utils.generate_success_message(inter, Strings.lottery_update_no_active_lotteries)

      results, guesses_cleared = result
      await message_utils.generate_success_message(inter, Strings.lottery_update_success(results=results, guesses_cleared=guesses_cleared))

  @data_manager.sub_command(description=Strings.data_manager_remove_event_items_description)
  @cooldowns.short_cooldown
  @permissions.bot_developer()
  async def remove_event_items(self, inter: disnake.CommandInteraction,
                               event_identifier = commands.Param(default=None, description=Strings.dt_event_identifier_param_description, autocomplete=dt_autocomplete.autocomplete_event_identifier, converter=dt_autocomplete.event_identifier_converter, convert_defaults=True)):
    await inter.response.defer(with_message=True, ephemeral=True)

    if await dt_items_repo.remove_event_participation_items(event_identifier[0], event_identifier[1]):
      await message_utils.generate_success_message(inter, Strings.data_manager_remove_event_items_success(event_year=event_identifier[0], event_week=event_identifier[1]))
    else:
      await message_utils.generate_error_message(inter, Strings.data_manager_remove_event_items_failed(event_year=event_identifier[0], event_week=event_identifier[1]))

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
          ammount = int(row["amount"])

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

          member = await dt_guild_member_repo.create_dummy_dt_guild_member(user_id, guild_id)
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

def setup(bot):
  bot.add_cog(DTDynamicDataManager(bot))
