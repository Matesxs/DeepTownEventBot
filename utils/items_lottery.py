import asyncio
import disnake
import datetime
from typing import Optional, List, Dict, Union, Tuple
from table2ascii import table2ascii, Alignment

from config.strings import Strings
from features.base_bot import BaseAutoshardedBot
from database import dt_event_item_lottery_repo, discord_objects_repo
from utils.logger import setup_custom_logger
from utils import string_manipulation, object_getters, dt_helpers, message_utils

logger = setup_custom_logger(__name__)

async def process_loterries(bot: BaseAutoshardedBot):
  async def process_lottery_result(lottery: dt_event_item_lottery_repo.DTEventItemLottery, result: Tuple[int, Optional[Dict[int, List[discord_objects_repo.DiscordUser]]]]):
    guild = await lottery.guild.to_object(bot)

    destination = await lottery.get_lotery_message(bot)
    if destination is None:
      destination = await lottery.get_lotery_channel(bot)

    if destination is None:
      logger.warning(f"Failed to get any destination for guild `{guild.name if guild is not None else lottery.guild_id}` and lottery `{lottery.id}`")
      return

    if isinstance(destination, disnake.Message):
      try:
        embed = destination.embeds[0]
        embed.description = f"**Ended**\n" + embed.description

        buttons = [disnake.ui.Button(emoji="🗑️", custom_id=f"event_item_lottery:remove:{lottery.id}", style=disnake.ButtonStyle.red),
                   disnake.ui.Button(emoji="🔁", custom_id=f"event_item_lottery:repeat:{lottery.id}", style=disnake.ButtonStyle.primary)]

        await destination.edit(embed=embed, components=buttons)
      except:
        pass

    author = await lottery.get_author(bot)
    if author is None:
      author_name = lottery.user.name
    else:
      author_name = author.display_name

    if result[1] is None:
      message = f"Items guess lottery result for event `{lottery.event_specification.event_year} {lottery.event_specification.event_week}` by {author_name}\nParticipants: {result[0]}\n**This event didn't have items set so there are no winners**"
      if isinstance(destination, disnake.Message):
        await destination.reply(message)
      else:
        await destination.send(message)
    else:
      table_data = []

      positions = list(result[1].keys())
      positions.sort(reverse=True)
      if not positions:
        message = f"Event items lottery result for `{lottery.event_specification.event_year} {lottery.event_specification.event_week}` by {author_name}\nParticipants: {result[0]}\n**There are no winners**"
        if isinstance(destination, disnake.Message):
          await destination.reply(message)
        else:
          await destination.send(message)
        return

      for position in positions:
        if position == 1:
          if lottery.guessed_1_reward_item_name is None or lottery.guessed_1_item_reward_amount <= 0: continue
          reward_item_amount = lottery.guessed_1_item_reward_amount
          reward_item_name = lottery.guessed_1_reward_item_name
        elif position == 2:
          if lottery.guessed_2_reward_item_name is None or lottery.guessed_2_item_reward_amount <= 0: continue
          reward_item_amount = lottery.guessed_2_item_reward_amount
          reward_item_name = lottery.guessed_2_reward_item_name
        elif position == 3:
          if lottery.guessed_3_reward_item_name is None or lottery.guessed_3_item_reward_amount <= 0: continue
          reward_item_amount = lottery.guessed_3_item_reward_amount
          reward_item_name = lottery.guessed_3_reward_item_name
        elif position == 4:
          if lottery.guessed_4_reward_item_name is None or lottery.guessed_4_item_reward_amount <= 0: continue
          reward_item_amount = lottery.guessed_4_item_reward_amount
          reward_item_name = lottery.guessed_4_reward_item_name
        else:
          continue

        winner_names = []
        for user in result[1][position]:
          guess_author = await user.to_object(bot)
          if guess_author is None:
            guess_author_name = user.name
          else:
            guess_author_name = guess_author.display_name
          winner_names.append(string_manipulation.truncate_string(guess_author_name, 15))

        reward = reward_item_amount / len(winner_names)
        table_data.append((position, f"{string_manipulation.format_number(reward)} {reward_item_name}", "\n".join(winner_names)))

      table_lines = [f"Event items lottery result for `{lottery.event_specification.event_year} {lottery.event_specification.event_week}` by {author_name}",
                     f"Participants: {result[0]}",
                     *("```\n" + table2ascii(["Guessed", "Reward each", "Winners"], table_data, alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.LEFT], first_col_heading=True) + "\n```").split("\n")]
      while table_lines:
        final_string, table_lines = string_manipulation.add_string_until_length(table_lines, 2000, "\n")
        if isinstance(destination, disnake.Message):
          destination = await destination.reply(final_string)
        else:
          await destination.send(final_string)
        await asyncio.sleep(0.005)



  not_closed_lotteries = await dt_event_item_lottery_repo.get_all_active_lotteries()
  if not not_closed_lotteries:
    await dt_event_item_lottery_repo.clear_old_guesses()
    return None

  results = [(lottery, await dt_event_item_lottery_repo.get_results(lottery)) for lottery in not_closed_lotteries]
  for lottery, result in results:
    await process_lottery_result(lottery, result)

  await dt_event_item_lottery_repo.close_all_active_lotteries()
  guesses_cleared = await dt_event_item_lottery_repo.clear_old_guesses()

  return len(results), guesses_cleared

async def create_lottery(inter: Union[disnake.CommandInteraction, disnake.MessageInteraction], lottery: dt_event_item_lottery_repo.DTEventItemLottery, can_show_guesses: bool, message: Optional[disnake.Message]=None):
  table_data = [(4, f"{string_manipulation.format_number(lottery.guessed_4_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_4_reward_item_name, 20)}" if lottery.guessed_4_reward_item_name is not None and lottery.guessed_4_item_reward_amount > 0 else "*No Reward*"),
                (3, f"{string_manipulation.format_number(lottery.guessed_3_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_3_reward_item_name, 20)}" if lottery.guessed_3_reward_item_name is not None and lottery.guessed_3_item_reward_amount > 0 else "*No Reward*"),
                (2, f"{string_manipulation.format_number(lottery.guessed_2_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_2_reward_item_name, 20)}" if lottery.guessed_2_reward_item_name is not None and lottery.guessed_2_item_reward_amount > 0 else "*No Reward*"),
                (1, f"{string_manipulation.format_number(lottery.guessed_1_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_1_reward_item_name, 20)}" if lottery.guessed_1_reward_item_name is not None and lottery.guessed_1_item_reward_amount > 0 else "*No Reward*")]
  lottery_table = table2ascii(["Guessed", "Reward"], table_data, alignments=[Alignment.RIGHT, Alignment.LEFT], first_col_heading=True)

  next_year, next_week = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))
  lottery_embed = disnake.Embed(title=f"Items guess lottery for event `{next_year} {next_week}` by {inter.author.display_name}", description=f"```\n{lottery_table}\n```\nUse `/lottery guess` to participate in lotteries", color=disnake.Color.blurple())
  message_utils.add_author_footer(lottery_embed, inter.author)

  if message is None:
    await inter.send(embed=lottery_embed)
    message = await inter.original_message()
    if message is None:
      await dt_event_item_lottery_repo.remove_lottery(lottery.id)
      return await message_utils.generate_error_message(inter, Strings.lottery_create_failed_to_get_lottery_message)
  else:
    await message.edit(embed=lottery_embed)

  lottery.lottery_message_id = str(message.id)
  await dt_event_item_lottery_repo.run_commit()

  buttons = [disnake.ui.Button(emoji="🗑️", custom_id=f"event_item_lottery:remove:{lottery.id}", style=disnake.ButtonStyle.red)]
  if can_show_guesses:
    buttons.append(disnake.ui.Button(emoji="🧾", custom_id=f"event_item_lottery:show:{lottery.id}", style=disnake.ButtonStyle.blurple))
  await message.edit(components=buttons)

async def generate_guesses_tables(bot: BaseAutoshardedBot, lottery: dt_event_item_lottery_repo.DTEventItemLottery):
  data = []

  for guess in lottery.guesses:
    author = await lottery.get_author(bot) or await lottery.user.to_object(bot)
    if author is None:
      author_name = guess.user.name
    else:
      author_name = author.display_name

    if not guess.guessed_lotery_items: continue
    data.append((string_manipulation.truncate_string(author_name, 20), "\n".join([i.item_name for i in guess.guessed_lotery_items])))

  table_lines = table2ascii(["Guesser", "Items"], data).split("\n")
  tables = []
  while table_lines:
    table, table_lines = string_manipulation.add_string_until_length(table_lines, 1900, "\n")
    tables.append(table)

  return tables
