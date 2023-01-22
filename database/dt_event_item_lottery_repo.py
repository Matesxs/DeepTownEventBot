import asyncio
import datetime
import disnake
from sqlalchemy import select, delete
from typing import Optional, List, Dict

from database import run_query, run_commit, session, dt_items_repo, guilds_repo, event_participation_repo
from database.tables.dt_event_item_lottery import DTEventItemLottery, DTEventItemLotteryGuess, DTEventItemLotteryGuessedItem
from utils import dt_helpers

create_lotery_lock = asyncio.Lock()
create_lotery_guess_lock = asyncio.Lock()

async def get_event_item_lotery(id_: int) -> Optional[DTEventItemLottery]:
  result = await run_query(select(DTEventItemLottery).filter(DTEventItemLottery.id == id_))
  return result.scalar_one_or_none()

async def create_event_item_lotery(guild: disnake.Guild, author: disnake.User, message: disnake.Message,
                                   reward_item_g4: Optional[dt_items_repo.DTItem]=None, item_g4_amount: int=0,
                                   reward_item_g3: Optional[dt_items_repo.DTItem]=None, item_g3_amount: int=0,
                                   reward_item_g2: Optional[dt_items_repo.DTItem]=None, item_g2_amount: int=0,
                                   reward_item_g1: Optional[dt_items_repo.DTItem]=None, item_g1_amount: int=0) -> DTEventItemLottery:
  await guilds_repo.get_or_create_discord_guild(guild, True)

  year, week = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))
  event_specification = await event_participation_repo.get_or_create_event_specification(year, week)

  await create_lotery_lock.acquire()
  item = DTEventItemLottery(author_id=str(author.id), guild_id=str(guild.id), lotery_channel_id=str(message.channel.id), lotery_message_id=str(message.id), event_id=event_specification.event_id,
                            guessed_4_reward_item_name=reward_item_g4.name if reward_item_g4 is not None else None, guessed_4_item_reward_amount=item_g4_amount,
                            guessed_3_reward_item_name=reward_item_g3.name if reward_item_g3 is not None else None, guessed_3_item_reward_amount=item_g3_amount,
                            guessed_2_reward_item_name=reward_item_g2.name if reward_item_g2 is not None else None, guessed_2_item_reward_amount=item_g2_amount,
                            guessed_1_reward_item_name=reward_item_g1.name if reward_item_g1 is not None else None, guessed_1_item_reward_amount=item_g1_amount)
  session.add(item)
  await run_commit()
  create_lotery_lock.release()

  return item

async def get_guess(lotery_id: int, author_id: int) -> Optional[DTEventItemLotteryGuess]:
  result = await run_query(select(DTEventItemLotteryGuess).filter(DTEventItemLotteryGuess.lotery_id == lotery_id, DTEventItemLotteryGuess.user_id == str(author_id)))
  return result.scalar_one_or_none()

async def get_lotery_guesses(lotery_id: int) -> List[DTEventItemLotteryGuess]:
  result = await run_query(select(DTEventItemLotteryGuess).filter(DTEventItemLotteryGuess.lotery_id == lotery_id))
  return result.scalars().all()

async def make_guess(lotery_id: int, author: disnake.User, items: List[dt_items_repo.DTItem]) -> Optional[DTEventItemLotteryGuess]:
  lotery = await get_event_item_lotery(lotery_id)
  if lotery is None:
    return None

  if lotery.closed_at is not None:
    return None

  unique_item_names = list(dict([item.name for item in items]))
  if len(unique_item_names) != len(items):
    return None

  await create_lotery_guess_lock.acquire()
  guess = await get_guess(lotery_id, author.id)

  if guess is not None:
    # Guess already made so remove old items
    await run_query(delete(DTEventItemLotteryGuessedItem).filter(DTEventItemLotteryGuessedItem.guess_id == guess.id), commit=True)
  else:
    guess = DTEventItemLotteryGuess(lotery_id=lotery_id, user_id=str(author.id))
    session.add(guess)
    await run_commit()
  create_lotery_guess_lock.release()

  for item in items:
    guess_item = DTEventItemLotteryGuessedItem(guess_id=guess.id, item_name=item.name)
    session.add(guess_item)

  await run_commit()

  return guess

async def get_results(lotery_id: int) -> Optional[Dict[int, List[int]]]:
  """
  :param lotery_id: ID of lotery
  :return: dict of number of right guesses and coresponding guesser ids
  """
  lotery = await get_event_item_lotery(lotery_id)
  if lotery is None:
    return None

  event_items = list(lotery.event_specification.participation_items)
  if not event_items:
    return None

  event_item_names = [ei.item_name for ei in event_items]
  event_item_names_set = set(event_item_names)
  guesses = await get_lotery_guesses(lotery_id)

  results = {}
  for guess in guesses:
    author_id = guess.user_id
    guessed_items = list(guess.guessed_lotery_items)
    if not guessed_items: continue

    guessed_item_names = [gi.item_name for gi in guessed_items]

    guessed_right = len(event_item_names_set & set(guessed_item_names))
    if guessed_right == 0: continue

    if guessed_right not in results.keys():
      results[guessed_right] = [int(author_id)]
    else:
      results[guessed_right].append(int(author_id))

  return results