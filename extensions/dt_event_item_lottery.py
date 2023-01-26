import asyncio
import disnake
from typing import Optional
from disnake.ext import commands

from config import cooldowns, permissions
from config.strings import Strings
from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from utils import message_utils, dt_autocomplete, items_lottery
from database import dt_items_repo, dt_event_item_lottery_repo

logger = setup_custom_logger(__name__)

class DTEventItemLottery(Base_Cog):
  def __init__(self, bot):
    super(DTEventItemLottery, self).__init__(bot, __file__)

  @commands.slash_command(name="lottery")
  async def lottery_command(self, inter: disnake.CommandInteraction):
    pass

  @lottery_command.sub_command(name="create", description=Strings.lottery_create_description)
  @commands.guild_only()
  @cooldowns.long_cooldown
  async def create_lottery(self, inter: disnake.CommandInteraction,
                           guessed_4_reward_item: Optional[str] = commands.Param(default=None, description=Strings.lottery_create_reward_item_param_description(item_number=4), autocomplete=dt_autocomplete.autocomplete_item),
                           guessed_4_reward_item_amount: int=commands.Param(default=0, min_value=0, description=Strings.lottery_create_reward_item_amount_param_description(item_number=4)),
                           guessed_3_reward_item: Optional[str] = commands.Param(default=None, description=Strings.lottery_create_reward_item_param_description(item_number=3), autocomplete=dt_autocomplete.autocomplete_item),
                           guessed_3_reward_item_amount: int = commands.Param(default=0, min_value=0, description=Strings.lottery_create_reward_item_amount_param_description(item_number=3)),
                           guessed_2_reward_item: Optional[str] = commands.Param(default=None, description=Strings.lottery_create_reward_item_param_description(item_number=2), autocomplete=dt_autocomplete.autocomplete_item),
                           guessed_2_reward_item_amount: int = commands.Param(default=0, min_value=0, description=Strings.lottery_create_reward_item_amount_param_description(item_number=2)),
                           guessed_1_reward_item: Optional[str] = commands.Param(default=None, description=Strings.lottery_create_reward_item_param_description(item_number=1), autocomplete=dt_autocomplete.autocomplete_item),
                           guessed_1_reward_item_amount: int = commands.Param(default=0, min_value=0, description=Strings.lottery_create_reward_item_amount_param_description(item_number=1)),
                           can_show_guesses: bool=commands.Param(default=False, description=Strings.lottery_create_can_show_guesses_param_description)):
    await inter.response.defer(with_message=True)

    if guessed_4_reward_item is not None:
      guessed_4_reward_item_ = await dt_items_repo.get_dt_item(guessed_4_reward_item)
      if guessed_4_reward_item_ is None:
        return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guessed_4_reward_item))
      guessed_4_reward_item = guessed_4_reward_item_
    if guessed_3_reward_item is not None:
      guessed_3_reward_item_ = await dt_items_repo.get_dt_item(guessed_3_reward_item)
      if guessed_3_reward_item_ is None:
        return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guessed_3_reward_item))
      guessed_3_reward_item = guessed_3_reward_item_
    if guessed_2_reward_item is not None:
      guessed_2_reward_item_ = await dt_items_repo.get_dt_item(guessed_2_reward_item)
      if guessed_2_reward_item_ is None:
        return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guessed_2_reward_item))
      guessed_2_reward_item = guessed_2_reward_item_
    if guessed_1_reward_item is not None:
      guessed_1_reward_item_ = await dt_items_repo.get_dt_item(guessed_1_reward_item)
      if guessed_1_reward_item_ is None:
        return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guessed_1_reward_item))
      guessed_1_reward_item = guessed_1_reward_item_

    orig_message = await inter.original_message()
    lottery = await dt_event_item_lottery_repo.create_event_item_lottery(inter.guild, inter.author, orig_message.channel,
                                                                         guessed_4_reward_item, guessed_4_reward_item_amount,
                                                                         guessed_3_reward_item, guessed_3_reward_item_amount,
                                                                         guessed_2_reward_item, guessed_2_reward_item_amount,
                                                                         guessed_1_reward_item, guessed_1_reward_item_amount)
    if lottery is None:
      return await message_utils.generate_error_message(inter, Strings.lottery_create_lottery_already_created)

    await items_lottery.create_lottery(inter, lottery, can_show_guesses, orig_message)

  @lottery_command.sub_command(name="guess", description=Strings.lottery_guess_description)
  @commands.guild_only()
  @cooldowns.long_cooldown
  async def lottery_make_guess(self, inter: disnake.CommandInteraction,
                               guess_item_1: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=1), autocomplete=dt_autocomplete.autocomplete_item),
                               guess_item_2: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=2), autocomplete=dt_autocomplete.autocomplete_item),
                               guess_item_3: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=3), autocomplete=dt_autocomplete.autocomplete_item),
                               guess_item_4: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=4), autocomplete=dt_autocomplete.autocomplete_item)):
    await inter.response.defer(with_message=True, ephemeral=True)

    items = []
    if guess_item_1 is not None:
      guess_item_1_ = await dt_items_repo.get_dt_item(guess_item_1)
      if guess_item_1_ is None:
        return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guess_item_1))
      items.append(guess_item_1_)
    if guess_item_2 is not None:
      guess_item_2_ = await dt_items_repo.get_dt_item(guess_item_2)
      if guess_item_2_ is None:
        return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guess_item_2))
      items.append(guess_item_2_)
    if guess_item_3 is not None:
      guess_item_3_ = await dt_items_repo.get_dt_item(guess_item_3)
      if guess_item_3_ is None:
        return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guess_item_3))
      items.append(guess_item_3_)
    if guess_item_4 is not None:
      guess_item_4_ = await dt_items_repo.get_dt_item(guess_item_4)
      if guess_item_4_ is None:
        return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guess_item_4))
      items.append(guess_item_4_)

    guess = await dt_event_item_lottery_repo.make_next_event_guess(inter.guild, inter.author, items)
    if guess is None:
      return await message_utils.generate_error_message(inter, Strings.lottery_guess_item_duplicates)

    guessed_item_names_string = ", ".join([i.name for i in items])
    await message_utils.generate_success_message(inter, Strings.lottery_guess_registered(event_year=guess.event_specification.event_year, event_week=guess.event_specification.event_week, items=guessed_item_names_string))

  @lottery_command.sub_command(name="update", description=Strings.lottery_update_description)
  @commands.is_owner()
  @cooldowns.long_cooldown
  async def lottery_update(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    result = await items_lottery.process_loterries(self.bot)
    if result is None:
      return await message_utils.generate_success_message(inter, Strings.lottery_update_no_active_lotteries)

    results, guesses_cleared = result
    await message_utils.generate_success_message(inter, Strings.lottery_update_success(results=results, guesses_cleared=guesses_cleared))

  @commands.Cog.listener()
  async def on_button_click(self, inter: disnake.MessageInteraction):
    if not isinstance(inter.component, disnake.Button): return

    button_custom_id = inter.component.custom_id
    if button_custom_id is None or not button_custom_id.startswith("event_item_lottery"): return
    await inter.response.defer()

    data = button_custom_id.split(":")
    command = data[1]
    lottery_id = int(data[2])

    lottery = await dt_event_item_lottery_repo.get_event_item_lottery(lottery_id)
    if lottery is None:
      await message_utils.delete_message(self.bot, inter.message)
      return await message_utils.generate_error_message(inter, Strings.lottery_button_listener_invalid_lottery)

    if command == "remove":
      if inter.author.id == int(lottery.author_id) or (int(lottery.author_id) != self.bot.owner_id and (await permissions.predicate_is_guild_administrator(inter))):
        await message_utils.delete_message(self.bot, inter.message)
        await dt_event_item_lottery_repo.remove_lottery(lottery.id)
        await message_utils.generate_success_message(inter, Strings.lottery_button_listener_removed)
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    elif command == "show":
      for table in (await items_lottery.generate_guesses_tables(self.bot, lottery)):
        await inter.send(f"```\n{table}\n```", ephemeral=True)
        await asyncio.sleep(0.05)
    elif command == "repeat":
      if inter.author.id == int(lottery.author_id) or (int(lottery.author_id) != self.bot.owner_id and (await permissions.predicate_is_guild_administrator(inter))):
        message = await inter.original_response()
        new_lottery = await lottery.repeat()
        await items_lottery.create_lottery(inter, new_lottery, len(message.components) > 1, message)
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    else:
      await message_utils.generate_error_message(inter, Strings.lottery_button_listener_invalid_command)

def setup(bot):
  bot.add_cog(DTEventItemLottery(bot))
