import asyncio
import disnake
import datetime
from typing import Optional, List, Dict, Union
from table2ascii import table2ascii, Alignment

from config.strings import Strings
from features.base_bot import BaseAutoshardedBot
from database import dt_event_item_lottery_repo
from utils.logger import setup_custom_logger
from utils import string_manipulation, object_getters, dt_helpers, message_utils

logger = setup_custom_logger(__name__)

async def process_loterries(bot: BaseAutoshardedBot):
  async def process_lottery_result(lottery: dt_event_item_lottery_repo.DTEventItemLottery, result: Optional[Dict[int, List[int]]]):
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

    if result is None:
      message = f"```\nItems guess lottery result for event `{lottery.event_specification.event_year} {lottery.event_specification.event_week}`\n**This event didn't have items set so there are no winners**\n```"
      if isinstance(destination, disnake.Message):
        await destination.reply(message)
      else:
        await destination.send(message)
    else:
      table_data = []

      positions = list(result.keys())
      positions.sort(reverse=True)
      if not positions:
        message = f"```\nEvent items lottery result for `{lottery.event_specification.event_year} {lottery.event_specification.event_week}`\n**There are no winners**\n```"
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

        winners: List[Optional[disnake.Member]] = await asyncio.gather(*[object_getters.get_or_fetch_member(guild if guild is not None else bot, uid) for uid in result[position]])
        winner_names = [string_manipulation.truncate_string(w.display_name, 15) for w in winners if w is not None]
        reward = reward_item_amount / len(winner_names)
        table_data.append((position, f"{string_manipulation.format_number(reward)} {reward_item_name}", "\n".join(winner_names)))

      author = await lottery.get_author(bot)
      table_lines = [f"Event items lottery result for `{lottery.event_specification.event_year} {lottery.event_specification.event_week}` by {author.display_name if author is not None else '*Unknown*'}",
                     *table2ascii(["Guessed", "Reward each", "Winners"], table_data, alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.LEFT], first_col_heading=True).split("\n")]
      while table_lines:
        final_string, table_lines = string_manipulation.add_string_until_length(table_lines, 2000, "\n")
        if isinstance(destination, disnake.Message):
          destination = await destination.reply(final_string)
        else:
          await destination.send(final_string)
        await asyncio.sleep(0.005)

  not_closed_lotteries = await dt_event_item_lottery_repo.get_all_active_lotteries()
  if not not_closed_lotteries:
    return None

  results = [(lottery, await dt_event_item_lottery_repo.get_results(lottery)) for lottery in not_closed_lotteries]
  for lottery, result in results:
    if result is None:
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