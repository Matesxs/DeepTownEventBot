import disnake
from disnake.ext import commands
from typing import Optional, Tuple
import asyncio
import math
from Levenshtein import ratio
import datetime

from features.base_cog import Base_Cog
from utils import message_utils, dt_autocomplete, items_lottery, command_utils, dt_helpers
from utils.logger import setup_custom_logger
from config import cooldowns, Strings, permissions, config
from database import dt_items_repo, session_maker, run_commit_in_thread
from features.views import confirm_view

logger = setup_custom_logger(__name__)

async def update_event_items(inter, bot,
                             item1: str, item2: str, item3: str, item4: str,
                             base_amount1: Optional[int], base_amount2: Optional[int], base_amount3: Optional[int], base_amount4: Optional[int],
                             event_identifier: Optional[Tuple[int, int]],
                             current_level: int = 0,
                             update_loterries: bool = True):
  if event_identifier is None:
    event_identifier = dt_helpers.get_event_index(datetime.datetime.utcnow())

  with session_maker() as session:
    if (await dt_items_repo.get_dt_item(session, item1)) is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_item_not_in_database(item=item1))

    if (await dt_items_repo.get_dt_item(session, item2)) is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_item_not_in_database(item=item2))

    if (await dt_items_repo.get_dt_item(session, item3)) is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_item_not_in_database(item=item3))

    if (await dt_items_repo.get_dt_item(session, item4)) is None:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_item_not_in_database(item=item4))

    if len(list(set(list([item1, item2, item3, item4])))) != 4:
      return await message_utils.generate_error_message(inter, Strings.data_manager_set_event_items_repeated_items)

    await dt_items_repo.remove_event_participation_items(session, event_identifier[0], event_identifier[1])
    await asyncio.sleep(0.01)

    if current_level != 0:
      base_amount1 = math.ceil(base_amount1 / (0.9202166811 * math.exp((current_level + 1) / 8))) if base_amount1 is not None else None
      base_amount2 = math.ceil(base_amount2 / (0.9202166811 * math.exp((current_level + 1) / 8))) if base_amount2 is not None else None
      base_amount3 = math.ceil(base_amount3 / (0.9202166811 * math.exp((current_level + 1) / 8))) if base_amount3 is not None else None
      base_amount4 = math.ceil(base_amount4 / (0.9202166811 * math.exp((current_level + 1) / 8))) if base_amount4 is not None else None

    await dt_items_repo.set_event_item(session, event_identifier[0], event_identifier[1], item1, base_amount1, commit=False)
    await dt_items_repo.set_event_item(session, event_identifier[0], event_identifier[1], item2, base_amount2, commit=False)
    await dt_items_repo.set_event_item(session, event_identifier[0], event_identifier[1], item3, base_amount3, commit=False)
    await dt_items_repo.set_event_item(session, event_identifier[0], event_identifier[1], item4, base_amount4, commit=False)
    await run_commit_in_thread(session)

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

  if update_loterries:
    with session_maker() as session:
      result = await items_lottery.process_loterries(session, bot)
      if result is None:
        return await message_utils.generate_success_message(inter, Strings.lottery_update_no_active_lotteries)

      results, guesses_cleared = result

    await message_utils.generate_success_message(inter, Strings.lottery_update_success(results=results, guesses_cleared=guesses_cleared))

class DTDynamicDataManager(Base_Cog):
  def __init__(self, bot):
    super(DTDynamicDataManager, self).__init__(bot, __file__)

  @command_utils.master_only_slash_command(name="data_manager")
  async def dynamic_data_manager_commands(self, inter: disnake.CommandInteraction):
    pass

  @dynamic_data_manager_commands.sub_command(description=Strings.data_manager_set_event_items_description)
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

    await update_event_items(inter, self.bot,
                             item1, item2, item3, item4,
                             base_amount1, base_amount2, base_amount3, base_amount4,
                             event_identifier,
                             current_level,
                             update_items_lotteries)

  @commands.Cog.listener()
  async def on_message(self, message: disnake.Message):
    if message.author.bot or message.author.system: return
    if message.content == "" or message.content.startswith(config.base.command_prefix): return
    if message.guild is not None:
      if message.channel.id not in config.data_manager.automatic_set_event_items_channel_ids: return
      if not message.channel.permissions_for(message.guild.me).send_messages: return
    if not ((await self.bot.is_owner(message.author)) or message.author.id in config.base.developer_ids): return
    if not message.content.lower().startswith("event items"): return

    message_lines = message.content.strip().split("\n")[1:]
    number_of_lines = len(message_lines)
    if number_of_lines < 5 or number_of_lines > 6: return False

    with session_maker() as session:
      all_item_names = await dt_items_repo.get_all_item_names(session)
      all_item_names_processes = [(name, name.lower()) for name in all_item_names]

    identifier = None
    level = 0
    item_data = []
    for line in message_lines:
      splits = line.strip().split(" ")
      if splits[0].lower() == "event" and len(splits) == 3 and splits[1].isdecimal() and splits[2].isdecimal():
        identifier = (int(splits[1]), int(splits[2]))
      elif splits[0].lower() == "level" and len(splits) == 2 and splits[1].isdecimal():
        level = int(splits[1])
      else:
        amount = None
        if splits[-1].isdecimal():
          item_name = " ".join(splits[:-1])
          amount = int(splits[-1])
        else:
          item_name = line

        item_name = item_name.lower()

        max_score = 0
        guessed_item_name = None
        for true_item_name, true_item_name_lower in all_item_names_processes:
          score = ratio(item_name, true_item_name_lower)
          if score <= 0.1: continue

          if score > max_score:
            max_score = score
            guessed_item_name = true_item_name

          if max_score > 0.9:
            break

        if max_score > 0.5:
          item_data.append([guessed_item_name, amount])

    if len(item_data) != 4:
      return await message_utils.generate_error_message(message, Strings.data_manager_set_event_items_prompt_not_enough_items)

    if level < 0:
      return await message_utils.generate_error_message(message, Strings.data_manager_set_event_items_prompt_invalid_level)

    if level != 0:
      for i in range(4):
        item_data[i][1] = math.ceil(item_data[i][1] / (0.9202166811 * math.exp((level + 1) / 8)))

    items_list_string = "\n".join([f"`{item_name}` - {amount}" for item_name, amount in item_data])
    prompt_string = f"Event items\nAre these items correct?\n\n**Event identifier:** {identifier if identifier is not None else 'Current'}\n**Event level:** {level}\n**Event items:**\n{items_list_string}"
    confirmation_view = confirm_view.ConfirmView(message, prompt_string)
    if await confirmation_view.run():
      await confirmation_view.wait()

      if confirmation_view.get_result():
        await update_event_items(message, self.bot,
                                 item_data[0][0], item_data[1][0], item_data[2][0], item_data[3][0],
                                 item_data[0][1], item_data[1][1], item_data[2][1], item_data[3][1],
                                 identifier,
                                 0,
                                 True)

  @dynamic_data_manager_commands.sub_command(description=Strings.data_manager_remove_event_items_description)
  @cooldowns.short_cooldown
  @permissions.bot_developer()
  async def remove_event_items(self, inter: disnake.CommandInteraction,
                               event_identifier = commands.Param(default=None, description=Strings.dt_event_identifier_param_description, autocomplete=dt_autocomplete.autocomplete_event_identifier, converter=dt_autocomplete.event_identifier_converter, convert_defaults=True)):
    await inter.response.defer(with_message=True, ephemeral=True)

    with session_maker() as session:
      if await dt_items_repo.remove_event_participation_items(session, event_identifier[0], event_identifier[1]):
        await message_utils.generate_success_message(inter, Strings.data_manager_remove_event_items_success(event_year=event_identifier[0], event_week=event_identifier[1]))
      else:
        await message_utils.generate_error_message(inter, Strings.data_manager_remove_event_items_failed(event_year=event_identifier[0], event_week=event_identifier[1]))

def setup(bot):
  bot.add_cog(DTDynamicDataManager(bot))
