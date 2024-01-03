import asyncio
import datetime

import disnake
from typing import Optional
from disnake.ext import commands, tasks

from config import cooldowns, permissions
from config.strings import Strings
from config import config
from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from utils import message_utils, dt_autocomplete, items_lottery, dt_helpers
from database import dt_items_repo, dt_event_item_lottery_repo, run_commit, event_participation_repo

logger = setup_custom_logger(__name__)

async def make_guess(inter: disnake.CommandInteraction,
                     author: disnake.Member,
                     guess_item_1: Optional[str],
                     guess_item_2: Optional[str],
                     guess_item_3: Optional[str],
                     guess_item_4: Optional[str]):
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

  if not items:
    return await message_utils.generate_error_message(inter, Strings.lottery_guess_no_items)

  guess = await dt_event_item_lottery_repo.make_next_event_guess(author, items)
  if guess is None:
    return await message_utils.generate_error_message(inter, Strings.lottery_guess_item_duplicates)

  guessed_item_names_string = ", ".join([i.name for i in items])
  await message_utils.generate_success_message(inter, Strings.lottery_guess_registered(event_year=guess.event_specification.event_year, event_week=guess.event_specification.event_week, items=guessed_item_names_string))

class DTEventItemLottery(Base_Cog):
  def __init__(self, bot):
    super(DTEventItemLottery, self).__init__(bot, __file__)

  @commands.Cog.listener()
  async def on_ready(self):
    if not self.delete_long_closed_lotteries_task.is_running():
      self.delete_long_closed_lotteries_task.start()

    if not self.notify_lottery_closed_task.is_running():
      self.notify_lottery_closed_task.start()

  def cog_load(self) -> None:
    if self.bot.is_ready():
      if not self.delete_long_closed_lotteries_task.is_running():
        self.delete_long_closed_lotteries_task.start()

      if not self.notify_lottery_closed_task.is_running():
        self.notify_lottery_closed_task.start()

  def cog_unload(self) -> None:
    if self.delete_long_closed_lotteries_task.is_running():
      self.delete_long_closed_lotteries_task.cancel()

    if self.notify_lottery_closed_task.is_running():
      self.notify_lottery_closed_task.cancel()

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
                           guessed_1_reward_item_amount: int = commands.Param(default=0, min_value=0, description=Strings.lottery_create_reward_item_amount_param_description(item_number=1))):
    await inter.response.defer(with_message=True)

    if (guessed_4_reward_item is None or guessed_4_reward_item_amount == 0) and \
        (guessed_3_reward_item is None or guessed_3_reward_item_amount == 0) and \
        (guessed_2_reward_item is None or guessed_2_reward_item_amount == 0) and \
        (guessed_1_reward_item is None or guessed_1_reward_item_amount == 0):
      return await message_utils.generate_error_message(inter, Strings.lottery_create_no_reward_set)

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
    lottery = await dt_event_item_lottery_repo.create_event_item_lottery(inter.author, orig_message.channel,
                                                                         guessed_4_reward_item, guessed_4_reward_item_amount,
                                                                         guessed_3_reward_item, guessed_3_reward_item_amount,
                                                                         guessed_2_reward_item, guessed_2_reward_item_amount,
                                                                         guessed_1_reward_item, guessed_1_reward_item_amount)
    if lottery is None:
      return await message_utils.generate_error_message(inter, Strings.lottery_already_created)

    await items_lottery.create_lottery(inter.author, orig_message, lottery, True)

  @lottery_command.sub_command(name="update", description=Strings.lottery_update_description)
  @permissions.bot_developer()
  @cooldowns.long_cooldown
  async def lottery_update(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    result = await items_lottery.process_loterries(self.bot)
    if result is None:
      return await message_utils.generate_success_message(inter, Strings.lottery_update_no_active_lotteries)

    results, guesses_cleared = result
    await message_utils.generate_success_message(inter, Strings.lottery_update_success(results=results, guesses_cleared=guesses_cleared))

  @lottery_command.sub_command_group(name="guess")
  @commands.guild_only()
  @cooldowns.long_cooldown
  async def guess_commands(self, inter: disnake.CommandInteraction):
    pass

  @guess_commands.sub_command(name="create", description=Strings.lottery_guess_create_description)
  async def lottery_make_guess(self, inter: disnake.CommandInteraction,
                               guess_item_1: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=1), autocomplete=dt_autocomplete.autocomplete_item),
                               guess_item_2: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=2), autocomplete=dt_autocomplete.autocomplete_item),
                               guess_item_3: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=3), autocomplete=dt_autocomplete.autocomplete_item),
                               guess_item_4: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=4), autocomplete=dt_autocomplete.autocomplete_item)):
    await inter.response.defer(with_message=True, ephemeral=True)

    await make_guess(inter, inter.author, guess_item_1, guess_item_2, guess_item_3, guess_item_4)

  @guess_commands.sub_command(name="remove", description=Strings.lottery_guess_remove_description)
  async def lottery_remove_guess(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    year, week = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))
    event_specification = await event_participation_repo.get_or_create_event_specification(year, week)

    if await dt_event_item_lottery_repo.remove_guess(inter.guild_id, inter.author.id, event_specification.event_id):
      await message_utils.generate_success_message(inter, Strings.lottery_guess_removed_sucessfully)
    else:
      await message_utils.generate_error_message(inter, Strings.lottery_guess_no_guess_to_remove)

  @lottery_command.sub_command_group(name="guess_for")
  @commands.guild_only()
  @permissions.guild_administrator_role()
  @cooldowns.long_cooldown
  async def guess_for_commands(self, inter: disnake.CommandInteraction):
    pass

  @guess_for_commands.sub_command(name="create", description=Strings.lottery_guess_for_create_description)
  async def lottery_make_guess_for(self, inter: disnake.CommandInteraction,
                                   author: disnake.Member = commands.Param(description=Strings.lottery_guess_for_author_param_description),
                                   guess_item_1: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=1), autocomplete=dt_autocomplete.autocomplete_item),
                                   guess_item_2: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=2), autocomplete=dt_autocomplete.autocomplete_item),
                                   guess_item_3: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=3), autocomplete=dt_autocomplete.autocomplete_item),
                                   guess_item_4: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=4), autocomplete=dt_autocomplete.autocomplete_item)):
    await inter.response.defer(with_message=True, ephemeral=True)

    await make_guess(inter, author, guess_item_1, guess_item_2, guess_item_3, guess_item_4)

  @guess_for_commands.sub_command(name="remove", description=Strings.lottery_guess_for_remove_description)
  async def lottery_remove_guess_for(self, inter: disnake.CommandInteraction,
                                     author: disnake.Member = commands.Param(description=Strings.lottery_guess_for_author_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    year, week = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))
    event_specification = await event_participation_repo.get_or_create_event_specification(year, week)

    if await dt_event_item_lottery_repo.remove_guess(inter.guild_id, author.id, event_specification.event_id):
      await message_utils.generate_success_message(inter, Strings.lottery_guess_removed_sucessfully)
    else:
      await message_utils.generate_error_message(inter, Strings.lottery_guess_no_guess_to_remove)

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

    is_author = (inter.author.id == int(lottery.author_id)) or (await permissions.predicate_bot_developer(inter))

    if command == "remove":
      if is_author or (await permissions.predicate_guild_administrator_role(inter)):
        await message_utils.delete_message(self.bot, inter.message)
        await dt_event_item_lottery_repo.remove_lottery(lottery.id)
        await message_utils.generate_success_message(inter, Strings.lottery_button_listener_removed)
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    elif command == "show":
      if inter.guild is None or str(inter.guild.id) != lottery.guild_id:
        await message_utils.generate_error_message(inter, Strings.unexpected_action)
      else:
        for table in (await items_lottery.generate_guesses_tables(self.bot, lottery)):
          await inter.send(f"```\n{table}\n```", ephemeral=True, delete_after=60)
          await asyncio.sleep(0.05)
    elif command == "repeat":
      if is_author:
        next_event_lottery = await dt_event_item_lottery_repo.get_next_event_item_lottery_by_constrained(int(lottery.author_id), int(lottery.guild_id))
        if next_event_lottery is None:
          message = await inter.original_message()
          await lottery.repeat()
          await items_lottery.create_lottery(lottery.member.name, message, lottery, False)
        else:
          await message_utils.generate_error_message(inter, Strings.lottery_already_created)
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    elif command == "split_rewards":
      if is_author:
        lottery.split_rewards = not lottery.split_rewards
        await run_commit()

        await inter.edit_original_response(components=items_lottery.get_lottery_buttons(lottery))
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    elif command == "auto_repeat":
      if is_author:
        lottery.auto_repeat = not lottery.auto_repeat
        await run_commit()

        await inter.edit_original_response(components=items_lottery.get_lottery_buttons(lottery))
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    elif command == "auto_ping":
      if is_author:
        lottery.autoping_winners = not lottery.autoping_winners
        await run_commit()

        await inter.edit_original_response(components=items_lottery.get_lottery_buttons(lottery))
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    else:
      await message_utils.generate_error_message(inter, Strings.lottery_button_listener_invalid_command)

  @tasks.loop(hours=24 * config.lotteries.clean_old_lotteries_period_days)
  async def delete_long_closed_lotteries_task(self):
    lotteries_to_delete = await dt_event_item_lottery_repo.get_lotteries_closed_before_date(datetime.datetime.utcnow() - datetime.timedelta(days=config.lotteries.clean_lotteries_closed_for_more_than_days))

    if lotteries_to_delete:
      logger.info("Starting clearup of old closed lotteries")
      for lottery in lotteries_to_delete:
        await items_lottery.delete_lottery(self.bot, lottery)
        await asyncio.sleep(0.1)
      logger.info(f"Cleared {len(lotteries_to_delete)} old closed lotteries")

  @tasks.loop(time=datetime.time(hour=config.event_tracker.event_start_hour, minute=0, second=0))
  async def notify_lottery_closed_task(self):
    current_datetime = datetime.datetime.utcnow()

    if current_datetime.day == config.event_tracker.event_start_day:
      year, week = dt_helpers.get_event_index(current_datetime)
      lotteries_to_notify = await dt_event_item_lottery_repo.get_active_lotteries(year, week)

      if lotteries_to_notify:
        logger.info("Notifying that lotteries are closed")
        for lottery in lotteries_to_notify:
          await items_lottery.lottery_notify_closed_and_waiting(self.bot, lottery)
          await asyncio.sleep(0.1)
        logger.info(f"Notified {len(lotteries_to_notify)} lotteries")

def setup(bot):
  bot.add_cog(DTEventItemLottery(bot))
