import asyncio
import disnake
from typing import Optional, List, Dict, Tuple
from table2ascii import table2ascii, Alignment
from dateutil import tz

import database
from features.base_bot import BaseAutoshardedBot
from database import dt_event_item_lottery_repo, discord_objects_repo, run_commit
from database.tables import discord_objects
from utils.logger import setup_custom_logger
from utils import string_manipulation, message_utils, dt_report_generators, dt_helpers

logger = setup_custom_logger(__name__)

def create_lottery_embed(author: Optional[disnake.Member | disnake.User], lottery: dt_event_item_lottery_repo.DTEventItemLottery, closed: bool=False) -> disnake.Embed:
  table_data = [(4, f"{string_manipulation.format_number(lottery.guessed_4_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_4_reward_item_name, 20)}" if lottery.guessed_4_reward_item_name is not None and lottery.guessed_4_item_reward_amount > 0 else "*No Reward*"),
                (3, f"{string_manipulation.format_number(lottery.guessed_3_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_3_reward_item_name, 20)}" if lottery.guessed_3_reward_item_name is not None and lottery.guessed_3_item_reward_amount > 0 else "*No Reward*"),
                (2, f"{string_manipulation.format_number(lottery.guessed_2_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_2_reward_item_name, 20)}" if lottery.guessed_2_reward_item_name is not None and lottery.guessed_2_item_reward_amount > 0 else "*No Reward*"),
                (1, f"{string_manipulation.format_number(lottery.guessed_1_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_1_reward_item_name, 20)}" if lottery.guessed_1_reward_item_name is not None and lottery.guessed_1_item_reward_amount > 0 else "*No Reward*")]
  lottery_table = table2ascii(["Guessed", "Reward"], table_data, alignments=[Alignment.RIGHT, Alignment.LEFT], first_col_heading=True)

  year, week = lottery.event_specification.event_year, lottery.event_specification.event_week
  start_date, _ = dt_helpers.event_index_to_date_range(year, week)
  start_date = start_date.replace(tzinfo=tz.tzutc()).astimezone(tz.tzlocal())

  description_parts = [f"```\n{lottery_table}\n```"]
  if lottery.closed_at is None and not closed:
    description_parts.append(f"\nThis Event Starts <t:{int(start_date.timestamp())}>\nLottery Closing <t:{int(start_date.timestamp())}:R>\n")
  description_parts.append("Use `/lottery guess create` to participate in lotteries")
  description_string = "\n".join(description_parts)

  lottery_embed = disnake.Embed(title=f"Items guess lottery for event `{year} {week}` by {lottery.member.name}", description=description_string, color=disnake.Color.blurple())
  if author is not None:
    message_utils.add_author_footer(lottery_embed, author)
  return lottery_embed

async def delete_lottery(bot: BaseAutoshardedBot, lottery: dt_event_item_lottery_repo.DTEventItemLottery):
  lottery_message = await lottery.get_lotery_message(bot)
  if lottery_message is not None and lottery_message.author.id == bot.user.id:
    await lottery_message.edit(components=None)

  await database.remove_item(lottery)

async def lottery_notify_closed_and_waiting(bot: BaseAutoshardedBot, lottery: dt_event_item_lottery_repo.DTEventItemLottery):
  lottery_message = await lottery.get_lotery_message(bot)
  lottery_author = await lottery.get_author(bot)

  if lottery_message is not None and lottery_message.author.id == bot.user.id:
    embed = create_lottery_embed(lottery_author, lottery, closed=True)
    embed.description = "**Closed and waiting for evaluation**\n**!!No new guesses will count towards this lottery!!**\n\n" + embed.description

    await lottery_message.edit(embed=embed, components=None)

async def handle_closing_lottery_message(bot: BaseAutoshardedBot, message: disnake.Message, lottery: dt_event_item_lottery_repo.DTEventItemLottery, repeat: bool):
  lottery_author = await lottery.get_author(bot)

  if not repeat:
    embed = create_lottery_embed(lottery_author, lottery, closed=True)
    embed.description = "**Closed and results were send**\n\n" + embed.description

    buttons = [disnake.ui.Button(label="Delete", emoji="♻️", custom_id=f"event_item_lottery:remove:{lottery.id}", style=disnake.ButtonStyle.red),
               disnake.ui.Button(label="Repeat", emoji="🔂", custom_id=f"event_item_lottery:repeat:{lottery.id}", style=disnake.ButtonStyle.primary)]

    await message.edit(embed=embed, components=buttons)
  else:
    embed = create_lottery_embed(lottery_author, lottery, closed=True)
    embed.description = "**Closed and results were send**\n\n" + embed.description

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
    for user_object in result[1][position]:
      if isinstance(user_object, discord_objects.DiscordUser):
        winner_ids.append(int(user_object.id))
      elif isinstance(user_object, discord_objects.DiscordMember):
        winner_ids.append(int(user_object.user_id))
      else:
        continue

      winner_names.append(string_manipulation.truncate_string(user_object.name, 15))

    reward = (reward_item_amount / len(winner_names)) if lottery.split_rewards else reward_item_amount
    table_data.append((position, f"{string_manipulation.format_number(reward)} {reward_item_name}", ",\n".join(winner_names)))

  result_message_lines = [f"Event items lottery result for `{lottery.event_specification.event_year} {lottery.event_specification.event_week}` by {lottery.member.name}",
                          f"Participants: {result[0]}"]

  event_items_table_lines = dt_report_generators.get_event_items_table(lottery.event_specification, only_names=True).split("\n")
  while event_items_table_lines:
    final_string, event_items_table_lines = string_manipulation.add_string_until_length(event_items_table_lines, 1850, "\n")
    result_message_lines.append(f"```\n{final_string}\n```")

  if lottery.autoshow_guesses and len(lottery.guesses) > 0:
    for table in (await generate_guesses_tables(lottery)):
      result_message_lines.append(f"```\n{table}\n```")

  if winner_ids:
    rewards_table_lines = table2ascii(["Guessed", "Reward each", "Winners"], table_data, alignments=[Alignment.RIGHT, Alignment.LEFT, Alignment.LEFT], first_col_heading=True).split("\n")
    while rewards_table_lines:
      final_string, rewards_table_lines = string_manipulation.add_string_until_length(rewards_table_lines, 1850, "\n")
      result_message_lines.append(f"```\n{final_string}\n```")

    if lottery.autoping_winners:
      mention_strings = [f"<@{uid}>" for uid in winner_ids]

      while mention_strings:
        final_string, mention_strings = string_manipulation.add_string_until_length(mention_strings, 1850, " ")
        result_message_lines.append(final_string)

    result_message_lines.append("Congratulations to all winners! 🎉")
    result_message_lines.append("Don't forget to get get your rewards 😉")
  else:
    result_message_lines.append("**There are no winners**")
    result_message_lines.append("Better luck next time")

  destination = lottery_message or lottery_channel
  while result_message_lines:
    final_string, result_message_lines = string_manipulation.add_string_until_length(result_message_lines, 1900, "\n")
    if isinstance(destination, disnake.Message):
      destination = await destination.reply(final_string)
    else:
      destination = await destination.send(final_string)
    await asyncio.sleep(0.005)

  if lottery_message is not None and isinstance(destination, disnake.Message):
    await destination.edit(components=disnake.ui.Button(label="Jump to lottery", url=lottery_message.jump_url, style=disnake.ButtonStyle.primary))

  # Close or repeat lottery
  if lottery.auto_repeat:
    author = await lottery.get_author(bot)

    if author is not None:
      next_event_lottery = await dt_event_item_lottery_repo.get_next_event_item_lottery_by_constrained(int(lottery.author_id), int(lottery.guild_id))
      if next_event_lottery is None:
        if lottery_message is not None:
          await handle_closing_lottery_message(bot, lottery_message, lottery, True)

        await lottery.repeat()
        await create_lottery(author, lottery_message or destination, lottery, False)
      else:
        if lottery_message is not None:
          await handle_closing_lottery_message(bot, lottery_message, lottery, False)
        await lottery.close()
    else:
      if lottery_message is not None:
        await handle_closing_lottery_message(bot, lottery_message, lottery, False)
      await lottery.close()
  else:
    if lottery_message is not None:
      await handle_closing_lottery_message(bot, lottery_message, lottery, False)
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
               disnake.ui.Button(label="Auto Ping", emoji="📯", custom_id=f"event_item_lottery:auto_ping:{lottery.id}", style=disnake.ButtonStyle.success if lottery.autoping_winners else disnake.ButtonStyle.danger),
               disnake.ui.Button(label="Auto Show Guesses at End", emoji="📜", custom_id=f"event_item_lottery:auto_show_guesses:{lottery.id}", style=disnake.ButtonStyle.success if lottery.autoshow_guesses else disnake.ButtonStyle.danger)),
             disnake.ui.Button(label="Show participants", emoji="🧾", custom_id=f"event_item_lottery:show:{lottery.id}", style=disnake.ButtonStyle.blurple)]
  return buttons

async def create_lottery(author: disnake.Member | disnake.User, source_message: disnake.Message, lottery: dt_event_item_lottery_repo.DTEventItemLottery, replace_message: bool=False):
  lottery_embed = create_lottery_embed(author, lottery)

  if not replace_message:
    source_message = await source_message.reply(embed=lottery_embed)
  else:
    await source_message.edit(embed=lottery_embed)

  lottery.lottery_message_id = str(source_message.id)
  await run_commit()

  await source_message.edit(components=get_lottery_buttons(lottery))

async def generate_guesses_tables(lottery: dt_event_item_lottery_repo.DTEventItemLottery) -> list[str]:
  data = []

  for guess in lottery.guesses:
    if not guess.guessed_lotery_items: continue
    data.append((string_manipulation.truncate_string(guess.member.name, 20), ",\n".join([i.item_name for i in guess.guessed_lotery_items])))

  table_lines = table2ascii(["Guesser", "Items"], data, alignments=[Alignment.LEFT, Alignment.LEFT]).split("\n")
  tables = []
  while table_lines:
    table, table_lines = string_manipulation.add_string_until_length(table_lines, 1900, "\n")
    tables.append(table)

  return tables
