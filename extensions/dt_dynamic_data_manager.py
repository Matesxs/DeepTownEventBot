import disnake
from disnake.ext import commands
from typing import Optional
import asyncio
import math

from features.base_cog import Base_Cog
from utils import message_utils, dt_autocomplete, items_lottery, command_utils
from utils.logger import setup_custom_logger
from config import cooldowns, Strings, permissions
from database import dt_items_repo

logger = setup_custom_logger(__name__)

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

  @dynamic_data_manager_commands.sub_command(description=Strings.data_manager_remove_event_items_description)
  @cooldowns.short_cooldown
  @permissions.bot_developer()
  async def remove_event_items(self, inter: disnake.CommandInteraction,
                               event_identifier = commands.Param(default=None, description=Strings.dt_event_identifier_param_description, autocomplete=dt_autocomplete.autocomplete_event_identifier, converter=dt_autocomplete.event_identifier_converter, convert_defaults=True)):
    await inter.response.defer(with_message=True, ephemeral=True)

    if await dt_items_repo.remove_event_participation_items(event_identifier[0], event_identifier[1]):
      await message_utils.generate_success_message(inter, Strings.data_manager_remove_event_items_success(event_year=event_identifier[0], event_week=event_identifier[1]))
    else:
      await message_utils.generate_error_message(inter, Strings.data_manager_remove_event_items_failed(event_year=event_identifier[0], event_week=event_identifier[1]))

def setup(bot):
  bot.add_cog(DTDynamicDataManager(bot))
