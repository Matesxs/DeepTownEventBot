import asyncio
import disnake
import datetime
from typing import Optional, List, Dict, Union, Tuple
from table2ascii import table2ascii, Alignment

import database
from features.base_bot import BaseAutoshardedBot
from database import dt_event_item_lottery_repo, discord_objects_repo, run_commit
from utils.logger import setup_custom_logger
from utils import string_manipulation, dt_helpers, message_utils, dt_report_generators

logger = setup_custom_logger(__name__)

async def delete_lottery(bot: BaseAutoshardedBot, lottery: dt_event_item_lottery_repo.DTEventItemLottery):
  lottery_message = await lottery.get_lotery_message(bot)
  if lottery_message is not None and lottery_message.author.id == bot.user.id:
    await lottery_message.edit(components=None)

  await database.remove_item(lottery)

async def lottery_notify_closed_and_waiting(bot: BaseAutoshardedBot, lottery: dt_event_item_lottery_repo.DTEventItemLottery):
  lottery_message = await lottery.get_lotery_message(bot)
  if lottery_message is not None and lottery_message.author.id == bot.user.id:
    embed = lottery_message.embeds[0]
    embed.description = "**Closed and waiting for evaluation**\n**!!No new guesses will count towards this lottery!!**"

    await lottery_message.edit(embed=embed, components=None)

async def handle_closing_lottery_message(message: disnake.Message, lottery_id: int, repeat: bool):
  if not repeat:
    embed = message.embeds[0]
    embed.description = "**Ended**"

    buttons = [disnake.ui.Button(label="Delete", emoji="♻️", custom_id=f"event_item_lottery:remove:{lottery_id}", style=disnake.ButtonStyle.red),
               disnake.ui.Button(label="Repeat", emoji="🔂", custom_id=f"event_item_lottery:repeat:{lottery_id}", style=disnake.ButtonStyle.primary)]

    await message.edit(embed=embed, components=buttons)
  else:
    embed = message.embeds[0]
    embed.description = "**Ended**"

    await message.edit(embed=embed, components=None)

async def process_lottery_result(bot: BaseAutoshardedBot, lottery: dt_event_item_lottery_repo.DTEventItemLottery, result: Tuple[int, Optional[Dict[int, List[discord_objects_repo.DiscordUser]]]]):
  if result[1] is None: return

  guild = await lottery.guild.to_object(bot)

  lottery_message = await lottery.get_lotery_message(bot)
  if lottery_message.author.id != bot.user.id: lottery_message = None

  if lottery_message is None:
    lottery_channel = await lottery.get_lotery_channel(bot)
  else:
    lottery_channel = lottery_message.channel

  if lottery_message is None and lottery_channel is None:
    logger.warning(f"Failed to get any destination for guild `{guild.name if guild is not None else lottery.guild_id}` and lottery `{lottery.id}`")
    await delete_lottery(bot, lottery)
    return

  if lottery_message is not None:
    await handle_closing_lottery_message(lottery_message, lottery.id, lottery.auto_repeat)

  author = await lottery.get_author(bot)
  if author is None:
    author = await discord_objects_repo.get_discord_member(int(lottery.guild_id), int(lottery.author_id))
    author_name = author.name
  else:
    author_name = author.display_name

  positions = list(result[1].keys())
  positions.sort(reverse=True)

  table_data = []
  winner_ids = []
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
      winner_ids.append(int(user.id))

      if guess_author is None:
        guess_author = await discord_objects_repo.get_discord_member(int(lottery.guild_id), int(user.id))
        guess_author_name = guess_author.name
      else:
        guess_author_name = guess_author.display_name
      winner_names.append(string_manipulation.truncate_string(guess_author_name, 15))

    reward = (reward_item_amount / len(winner_names)) if lottery.split_rewards else reward_item_amount
    table_data.append((position, f"{string_manipulation.format_number(reward)} {reward_item_name}", ",\n".join(winner_names)))

  destination = lottery_message or lottery_channel

  event_items_table = dt_report_generators.get_event_items_table(lottery.event_specification, only_names=True)
  if not winner_ids:
    message = f"Event items lottery result for `{lottery.event_specification.event_year} {lottery.event_specification.event_week}` by {author_name}\nParticipants: {result[0]}\n```\n{event_items_table}\n```\n**There are no winners**"
    if isinstance(destination, disnake.Message):
      await destination.reply(message)
    else:
      await destination.send(message)
  else:
    table_lines = [f"Event items lottery result for `{lottery.event_specification.event_year} {lottery.event_specification.event_week}` by {author_name}",
                   f"Participants: {result[0]}",
                   *(f"```\n{event_items_table}\n```".split("\n")),
                   *("```\n" + table2ascii(["Guessed", "Reward each", "Winners"], table_data, alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.LEFT], first_col_heading=True) + "\n```").split("\n")]

    while table_lines:
      final_string, table_lines = string_manipulation.add_string_until_length(table_lines, 1900, "\n")
      if isinstance(destination, disnake.Message):
        destination = await destination.reply(final_string)
      else:
        destination = await destination.send(final_string)
      await asyncio.sleep(0.005)

    if lottery_message is not None and isinstance(destination, disnake.Message):
      await destination.edit(components=disnake.ui.Button(label="Jump to lottery", url=lottery_message.jump_url, style=disnake.ButtonStyle.primary))

    if winner_ids and lottery.autoping_winners:
      mention_strings = [f"<@{uid}>" for uid in winner_ids]

      while mention_strings:
        final_string, mention_strings = string_manipulation.add_string_until_length(mention_strings, 1800, " ")
        await destination.send(final_string)
        await asyncio.sleep(0.05)

  # Close or repeat lottery
  if lottery.auto_repeat:
    next_event_lottery = await dt_event_item_lottery_repo.get_next_event_item_lottery_by_constrained(int(lottery.author_id), int(lottery.guild_id))
    if next_event_lottery is None:
      await lottery.repeat()
      await create_lottery(author or author_name, (await lottery.get_lotery_message(bot)) or destination, lottery, False)
    else:
      await lottery.close()
  else:
    await lottery.close()

async def process_loterries(bot: BaseAutoshardedBot, year: Optional[int] = None, week: Optional[int] = None):
  not_closed_lotteries = await dt_event_item_lottery_repo.get_active_lotteries(year, week)
  if not not_closed_lotteries:
    await dt_event_item_lottery_repo.clear_old_guesses()
    return None

  results = [(lottery, await dt_event_item_lottery_repo.get_results(lottery)) for lottery in not_closed_lotteries]
  for lottery, result in results:
    if result[1] is None: continue
    await process_lottery_result(bot, lottery, result)
    await asyncio.sleep(0.005)

  guesses_cleared = await dt_event_item_lottery_repo.clear_old_guesses()

  return len(results), guesses_cleared

def get_lottery_buttons(lottery):
  buttons = [disnake.ui.ActionRow(
               disnake.ui.Button(label="Delete", emoji="♻️", custom_id=f"event_item_lottery:remove:{lottery.id}", style=disnake.ButtonStyle.red),
               disnake.ui.Button(label="Split rewards", emoji="🪓", custom_id=f"event_item_lottery:split_rewards:{lottery.id}", style=disnake.ButtonStyle.success if lottery.split_rewards else disnake.ButtonStyle.danger),
               disnake.ui.Button(label="Auto Repeat", emoji="🔁", custom_id=f"event_item_lottery:auto_repeat:{lottery.id}", style=disnake.ButtonStyle.success if lottery.auto_repeat else disnake.ButtonStyle.danger),
               disnake.ui.Button(label="Auto Ping", emoji="📯", custom_id=f"event_item_lottery:auto_ping:{lottery.id}", style=disnake.ButtonStyle.success if lottery.autoping_winners else disnake.ButtonStyle.danger)),
             disnake.ui.Button(label="Show participants", emoji="🧾", custom_id=f"event_item_lottery:show:{lottery.id}", style=disnake.ButtonStyle.blurple)]
  return buttons

async def create_lottery(author: Union[str, disnake.Member], source_message: disnake.Message, lottery: dt_event_item_lottery_repo.DTEventItemLottery, replace_message: bool=False):
  table_data = [(4, f"{string_manipulation.format_number(lottery.guessed_4_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_4_reward_item_name, 20)}" if lottery.guessed_4_reward_item_name is not None and lottery.guessed_4_item_reward_amount > 0 else "*No Reward*"),
                (3, f"{string_manipulation.format_number(lottery.guessed_3_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_3_reward_item_name, 20)}" if lottery.guessed_3_reward_item_name is not None and lottery.guessed_3_item_reward_amount > 0 else "*No Reward*"),
                (2, f"{string_manipulation.format_number(lottery.guessed_2_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_2_reward_item_name, 20)}" if lottery.guessed_2_reward_item_name is not None and lottery.guessed_2_item_reward_amount > 0 else "*No Reward*"),
                (1, f"{string_manipulation.format_number(lottery.guessed_1_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_1_reward_item_name, 20)}" if lottery.guessed_1_reward_item_name is not None and lottery.guessed_1_item_reward_amount > 0 else "*No Reward*")]
  lottery_table = table2ascii(["Guessed", "Reward"], table_data, alignments=[Alignment.RIGHT, Alignment.LEFT], first_col_heading=True)

  next_year, next_week = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))

  if isinstance(author, disnake.Member):
    lottery_embed = disnake.Embed(title=f"Items guess lottery for event `{next_year} {next_week}` by {author.display_name}", description=f"```\n{lottery_table}\n```\nUse `/lottery guess` to participate in lotteries", color=disnake.Color.blurple())
    message_utils.add_author_footer(lottery_embed, author)
  else:
    lottery_embed = disnake.Embed(title=f"Items guess lottery for event `{next_year} {next_week}` by {author}", description=f"```\n{lottery_table}\n```\nUse `/lottery guess` to participate in lotteries", color=disnake.Color.blurple())

  if not replace_message:
    source_message = await source_message.reply(embed=lottery_embed)
  else:
    await source_message.edit(embed=lottery_embed)

  lottery.lottery_message_id = str(source_message.id)
  await run_commit()

  await source_message.edit(components=get_lottery_buttons(lottery))

async def generate_guesses_tables(bot: BaseAutoshardedBot, lottery: dt_event_item_lottery_repo.DTEventItemLottery):
  data = []

  for guess in lottery.guesses:
    author = await guess.get_author(bot)
    if author is None:
      author = await discord_objects_repo.get_discord_member(int(guess.guild_id), int(guess.author_id))
      author_name = author.name
    else:
      author_name = author.display_name

    if not guess.guessed_lotery_items: continue
    data.append((string_manipulation.truncate_string(author_name, 20), ",\n".join([i.item_name for i in guess.guessed_lotery_items])))

  table_lines = table2ascii(["Guesser", "Items"], data, alignments=[Alignment.LEFT, Alignment.LEFT]).split("\n")
  tables = []
  while table_lines:
    table, table_lines = string_manipulation.add_string_until_length(table_lines, 1900, "\n")
    tables.append(table)

  return tables
