import datetime
import disnake
from disnake.ext import commands, tasks
from typing import Optional
import asyncio
import pandas as pd
import io
import traceback
from table2ascii import table2ascii
from table2ascii.alignment import Alignment

from features.base_cog import Base_Cog
from utils import dt_helpers, message_utils, string_manipulation, dt_identifier_autocomplete
from utils.logger import setup_custom_logger
from config import cooldowns, Strings, config
from database import event_participation_repo, tracking_settings_repo, dt_guild_repo, dt_guild_member_repo, guilds_repo, dt_items_repo, dt_blacklist_repo
from features.views.paginator import EmbedView

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

    self.all_item_names = dt_items_repo.get_all_dt_item_names()
    self.all_craftable_item_names = dt_items_repo.get_all_craftable_dt_item_names()

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
  async def update_guild(self, inter: disnake.CommandInteraction,
                         identifier: str=commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_identifier_autocomplete.autocomplete_identifier_guild)):
    await inter.response.defer(with_message=True, ephemeral=True)

    if identifier.isnumeric():
      guild_id = int(identifier)
    else:
      specifier = dt_identifier_autocomplete.identifier_to_specifier(identifier)
      if specifier is None:
        return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)
      guild_id = specifier[1]

    data = await dt_helpers.get_dt_guild_data(guild_id)
    if data is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_update_guild_get_failed(identifier=guild_id))

    event_participation_repo.generate_or_update_event_participations(data)

    await message_utils.generate_success_message(inter, Strings.data_manager_update_guild_success(guild=data.name))

  @data_manager.sub_command(description=Strings.data_manager_update_all_guilds_description)
  @cooldowns.long_cooldown
  @commands.is_owner()
  async def update_all_guilds(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    if config.data_manager.periodically_pull_data:
      self.data_update_task.restart()

      await message_utils.generate_success_message(inter, Strings.data_manager_update_all_guilds_success_with_periodic_update)
    else:
      guild_ids = await dt_helpers.get_ids_of_all_guilds()

      last_update = datetime.datetime.utcnow()

      if guild_ids is not None or not guild_ids:
        pulled_data = 0

        for idx, guild_id in enumerate(guild_ids):
          data = await dt_helpers.get_dt_guild_data(guild_id)
          if datetime.datetime.utcnow() - last_update > datetime.timedelta(seconds=10):
            await inter.edit_original_response(f"```\nGuild {idx+1}/{len(guild_ids)}\n```")
            last_update = datetime.datetime.utcnow()

          await asyncio.sleep(0.5)
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
        data = await dt_helpers.get_dt_guild_data(guild_id)
        if datetime.datetime.utcnow() - last_update > datetime.timedelta(seconds=10):
          await inter.edit_original_response(f"```\nGuild {idx + 1}/{len(guild_ids)}\n```")
          last_update = datetime.datetime.utcnow()

        await asyncio.sleep(0.5)
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

  @data_manager.sub_command_group(name="item")
  async def item_commands(self, inter: disnake.CommandInteraction):
    pass

  @item_commands.sub_command(name="add", description=Strings.data_manager_add_dt_item_description)
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def add_dt_item(self, inter: disnake.CommandInteraction,
                        name: str=commands.Param(description=Strings.data_manager_add_remove_dt_item_name_param_description),
                        item_type: dt_items_repo.ItemType=commands.Param(description=Strings.data_manager_add_dt_item_type_param_description),
                        item_source: dt_items_repo.ItemSource=commands.Param(description=Strings.data_manager_add_dt_item_source_param_description),
                        value: float=commands.Param(default=0.0, min_value=0.0, description=Strings.data_manager_add_dt_item_value_param_description),
                        crafting_time: float=commands.Param(default=0.0, min_value=0.0, description=Strings.data_manager_add_dt_item_crafting_time_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    item_type = dt_items_repo.ItemType(item_type)
    item_source = dt_items_repo.ItemSource(item_source)

    dt_items_repo.set_dt_item(name, item_type, item_source, value, crafting_time)

    self.all_item_names = dt_items_repo.get_all_dt_item_names()
    self.all_craftable_item_names = dt_items_repo.get_all_craftable_dt_item_names()

    if item_type == dt_items_repo.ItemType.CRAFTABLE:
      await message_utils.generate_success_message(inter, Strings.data_manager_add_dt_item_success_craftable(name=name, item_type=item_type, value=value, crafting_time=crafting_time))
    else:
      await message_utils.generate_success_message(inter, Strings.data_manager_add_dt_item_success_noncraftable(name=name, item_type=item_type, value=value))

  @item_commands.sub_command(name="remove", description=Strings.data_manager_remove_dt_item_description)
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def remove_dt_item(self, inter: disnake.CommandInteraction,
                           name: str=commands.Param(description=Strings.data_manager_add_remove_dt_item_name_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)
    if dt_items_repo.remove_dt_item(name):

      self.all_item_names = dt_items_repo.get_all_dt_item_names()
      self.all_craftable_item_names = dt_items_repo.get_all_craftable_dt_item_names()

      await message_utils.generate_success_message(inter, Strings.data_manager_remove_dt_item_success(name=name))
    else:
      await message_utils.generate_error_message(inter, Strings.data_manager_remove_dt_item_failed(name=name))

  @item_commands.sub_command(name="list", description=Strings.data_manager_list_dt_items_description)
  @cooldowns.default_cooldown
  async def list_dt_items(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    items = dt_items_repo.get_all_dt_items()
    if not items:
      return await message_utils.generate_error_message(inter, Strings.data_manager_list_dt_items_no_items)

    item_data = [(string_manipulation.truncate_string(item.name, 20), item.item_source, f"{string_manipulation.format_number(item.value, 2)}") for item in items]
    item_table_strings = table2ascii(["Name", "Source", "Value"], item_data, alignments=[Alignment.LEFT, Alignment.LEFT, Alignment.RIGHT]).split("\n")

    pages = []
    while item_table_strings:
      data_string, item_table_strings = string_manipulation.add_string_until_length(item_table_strings, 2000, "\n")
      embed = disnake.Embed(title="Deep Town Items", description=f"```\n{data_string}\n```", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(embed, inter.author)
      pages.append(embed)

    embed_view = EmbedView(inter.author, pages)
    await embed_view.run(inter)

  @item_commands.sub_command(name="modify_component", description=Strings.data_manager_modify_dt_item_component_description)
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def modify_dt_item_component(self, inter: disnake.CommandInteraction,
                                  target_item: str=commands.Param(description=Strings.data_manager_modify_dt_item_component_target_item_param_description),
                                  component_item: str=commands.Param(description=Strings.data_manager_modify_dt_item_component_component_item_param_description),
                                  amount: float=commands.Param(default=1.0, min_value=0.0, description=Strings.data_manager_modify_dt_item_component_amount_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    target_item_ = dt_items_repo.get_dt_item(target_item)
    if target_item_ is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_target_item_not_found)

    if target_item_.item_type != dt_items_repo.ItemType.CRAFTABLE:
      return await message_utils.generate_error_message(inter, Strings.data_manager_modify_dt_item_component_target_not_craftable)

    if dt_items_repo.get_dt_item(component_item) is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_modify_dt_item_component_component_not_found)

    if amount == 0:
      if dt_items_repo.remove_component_mapping(target_item, component_item):
        await message_utils.generate_success_message(inter, Strings.data_manager_modify_dt_item_component_removed(component_item=component_item, target_item=target_item))
      else:
        await message_utils.generate_error_message(inter, Strings.data_manager_modify_dt_item_component_remove_failed(component_item=component_item, target_item=target_item))
    else:
      dt_items_repo.set_component_mapping(target_item, component_item, amount)
      await message_utils.generate_success_message(inter, Strings.data_manager_modify_dt_item_component_added(target_item=target_item, component_item=component_item, amount=amount))

  @item_commands.sub_command(name="remove_components", description=Strings.data_manager_remove_dt_item_components_description)
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def remove_dt_item_components(self, inter: disnake.CommandInteraction,
                                      target_item: str=commands.Param(description=Strings.data_manager_remove_dt_item_components_target_item_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    target_item_ = dt_items_repo.get_dt_item(target_item)
    if target_item_ is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_target_item_not_found)

    if dt_items_repo.remove_all_component_mappings(target_item):
      await message_utils.generate_success_message(inter, Strings.data_manager_remove_dt_item_components_removed(target_item=target_item))
    else:
      await message_utils.generate_error_message(inter, Strings.data_manager_remove_dt_item_components_failed(target_item=target_item))

  @data_manager.sub_command(description=Strings.data_manager_set_event_items_description)
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def set_event_items(self, inter: disnake.CommandInteraction,
                            event_year: Optional[int]=commands.Param(default=None, min_value=0, description=Strings.dt_event_year_param_description),
                            event_week: Optional[int]=commands.Param(default=None, min_value=0, description=Strings.dt_event_week_param_description),
                            item1: str=commands.Param(description=Strings.data_manager_set_event_items_item_name_param_description(number=1)),
                            item2: str=commands.Param(description=Strings.data_manager_set_event_items_item_name_param_description(number=2)),
                            item3: str=commands.Param(description=Strings.data_manager_set_event_items_item_name_param_description(number=3)),
                            item4: str=commands.Param(description=Strings.data_manager_set_event_items_item_name_param_description(number=4)),
                            base_amount1: Optional[int]=commands.Param(default=None, min_value=0, description=Strings.data_manager_set_event_items_item_amount_param_description(number=1)),
                            base_amount2: Optional[int]=commands.Param(default=None, min_value=0, description=Strings.data_manager_set_event_items_item_amount_param_description(number=2)),
                            base_amount3: Optional[int]=commands.Param(default=None, min_value=0, description=Strings.data_manager_set_event_items_item_amount_param_description(number=3)),
                            base_amount4: Optional[int]=commands.Param(default=None, min_value=0, description=Strings.data_manager_set_event_items_item_amount_param_description(number=4))):
    await inter.response.defer(with_message=True, ephemeral=True)

    if event_year is None or event_week is None:
      event_year, event_week = dt_helpers.get_event_index(datetime.datetime.utcnow())

    if dt_items_repo.get_dt_item(item1) is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_item_not_in_database(item=item1))

    if dt_items_repo.get_dt_item(item2) is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_item_not_in_database(item=item2))

    if dt_items_repo.get_dt_item(item3) is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_item_not_in_database(item=item3))

    if dt_items_repo.get_dt_item(item4) is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_item_not_in_database(item=item4))

    unique_item_names = list(set(list([item1, item2, item3, item4])))
    if len(unique_item_names) != 4:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_repeated_items)

    dt_items_repo.remove_event_participation_items(event_year, event_week)
    await asyncio.sleep(0.01)

    dt_items_repo.set_event_item(event_year, event_week, item1, base_amount1, commit=False)
    dt_items_repo.set_event_item(event_year, event_week, item2, base_amount2, commit=False)
    dt_items_repo.set_event_item(event_year, event_week, item3, base_amount3, commit=False)
    dt_items_repo.set_event_item(event_year, event_week, item4, base_amount4, commit=False)
    dt_items_repo.session.commit()

    await message_utils.generate_success_message(inter, Strings.data_manager_set_event_items_success(event_year=event_year,
                                                                                                     event_week=event_week,
                                                                                                     item1=item1,
                                                                                                     item2=item2,
                                                                                                     item3=item3,
                                                                                                     item4=item4,
                                                                                                     base_amount1=base_amount1,
                                                                                                     base_amount2=base_amount2,
                                                                                                     base_amount3=base_amount3,
                                                                                                     base_amount4=base_amount4))

  @data_manager.sub_command(description=Strings.data_manager_remove_event_items_description)
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def remove_event_items(self, inter: disnake.CommandInteraction,
                               event_year: Optional[int]=commands.Param(default=None, min_value=0, description=Strings.dt_event_year_param_description),
                               event_week: Optional[int]=commands.Param(default=None, min_value=0, description=Strings.dt_event_week_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    if event_year is None or event_week is None:
      event_year, event_week = dt_helpers.get_event_index(datetime.datetime.utcnow())

    if dt_items_repo.remove_event_participation_items(event_year, event_week):
      await message_utils.generate_success_message(inter, Strings.data_manager_remove_event_items_success(event_year=event_year, event_week=event_week))
    else:
      await message_utils.generate_error_message(inter, Strings.data_manager_remove_event_items_failed(event_year=event_year, event_week=event_week))

  @set_event_items.autocomplete("item1")
  @set_event_items.autocomplete("item2")
  @set_event_items.autocomplete("item3")
  @set_event_items.autocomplete("item4")
  @remove_dt_item.autocomplete("name")
  @modify_dt_item_component.autocomplete("component_item")
  async def autocomplete_item(self, _, string: str):
    if string is None or not string: return self.all_item_names[:20]
    return [item for item in self.all_item_names if string.lower() in item.lower()][:20]

  @modify_dt_item_component.autocomplete("target_item")
  @remove_dt_item_components.autocomplete("target_item")
  async def autocomplete_craftable_item(self, _, string: str):
    if string is None or not string: return self.all_craftable_item_names[:20]
    return [item for item in self.all_craftable_item_names if string.lower() in item.lower()][:20]

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

          member = dt_guild_member_repo.create_dummy_dt_guild_member(user_id, guild_id)
          if member is None:
            continue

          if "username" in row.keys():
            member.user.username = row["username"]
          if "guild_name" in row.keys():
            member.guild.name = row["guild_name"]

          event_participation_repo.get_and_update_event_participation(user_id, guild_id, year, week, ammount)
          await asyncio.sleep(0.01)

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

  @data_manager.sub_command(description=Strings.data_manager_dump_guild_participation_data_description)
  @cooldowns.huge_cooldown
  async def dump_guild_participation_data(self, inter: disnake.CommandInteraction,
                                          identifier: str = commands.Param(description=Strings.dt_guild_identifier_param_description, autocomp=dt_identifier_autocomplete.autocomplete_identifier_guild)):
    await inter.response.defer(with_message=True, ephemeral=True)

    specifier = dt_identifier_autocomplete.identifier_to_specifier(identifier)
    if specifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    dump_data = event_participation_repo.dump_guild_event_participation_data(specifier[1])

    if not dump_data:
      return await message_utils.generate_error_message(inter, Strings.data_manager_dump_guild_participation_data_no_data(identifier=specifier[1]))

    dataframe = pd.DataFrame(dump_data, columns=["year", "week", "user_id", "username", "amount"], index=None)

    data = io.BytesIO()
    dataframe.to_csv(data, sep=";", index=False)

    data.seek(0)
    discord_file = disnake.File(data, filename=f"participations_guild_{specifier[1]}_dump.csv")

    await message_utils.generate_success_message(inter, Strings.data_manager_dump_guild_participation_data_success)
    await inter.send(file=discord_file)

  @tasks.loop(hours=config.data_manager.cleanup_rate_days * 24)
  async def cleanup_task(self):
    logger.info("Starting cleanup")
    all_guild_ids = await dt_helpers.get_ids_of_all_guilds()
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
    guild_ids = await dt_helpers.get_ids_of_all_guilds()
    await asyncio.sleep(0.1)

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

        if dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.GUILD, guild_id):
          continue

        data = await dt_helpers.get_dt_guild_data(guild_id)

        await asyncio.sleep(2)
        if data is None:
          not_updated.append(guild_id)
          continue

        event_participation_repo.generate_or_update_event_participations(data)
        await asyncio.sleep(0.1)
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

          if dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.GUILD, guild_id):
            continue

          data = await dt_helpers.get_dt_guild_data(guild_id)

          await asyncio.sleep(2)
          if data is None:
            continue

          not_updated.remove(guild_id)
          event_participation_repo.generate_or_update_event_participations(data)
          await asyncio.sleep(0.1)
          pulled_data += 1

      logger.info(f"Pulled data of {pulled_data} guilds\nGuilds {not_updated} not updated")
      self.skip_periodic_data_update = True
    logger.info("Guild data pull finished")

    await asyncio.sleep(30)
    await self.bot.change_presence(activity=disnake.Game(name=config.base.status_message), status=disnake.Status.online)

  @commands.Cog.listener()
  async def on_guild_joined(self, guild: disnake.Guild):
    guilds_repo.get_or_create_guild_if_not_exist(guild)

  @commands.Cog.listener()
  async def on_guild_remove(self, guild: disnake.Guild):
    guilds_repo.remove_guild(guild.id)

def setup(bot):
  bot.add_cog(DTDataManager(bot))
