import datetime
import disnake
from sqlalchemy import select, delete, or_, and_, text
from typing import Optional, List, Dict, Union, Tuple

from database import run_query, add_item, add_items, dt_items_repo, discord_objects_repo, event_participation_repo
from database.tables.dt_event_item_lottery import DTEventItemLottery, DTEventItemLotteryGuess, DTEventItemLotteryGuessedItem
from utils import dt_helpers

async def get_event_item_lottery(id_: int) -> Optional[DTEventItemLottery]:
  result = await run_query(select(DTEventItemLottery).filter(DTEventItemLottery.id == id_))
  return result.scalar_one_or_none()

async def get_event_item_lottery_by_constrained(author_id: int, guild_id: int, event_id: int) -> Optional[DTEventItemLottery]:
  result = await run_query(select(DTEventItemLottery).filter(DTEventItemLottery.author_id == str(author_id), DTEventItemLottery.guild_id == str(guild_id), DTEventItemLottery.event_id == event_id))
  return result.scalar_one_or_none()

async def get_next_event_item_lottery_by_constrained(author_id: int, guild_id: int) -> Optional[DTEventItemLottery]:
  next_year, next_week = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))
  event_specification = await event_participation_repo.get_or_create_event_specification(next_year, next_week)
  return await get_event_item_lottery_by_constrained(author_id, guild_id, event_specification.event_id)

async def event_lotery_exist(guild_id: int, author_id: int, event_id: int) -> bool:
  result = await run_query(select(DTEventItemLottery.id).filter(DTEventItemLottery.guild_id == str(guild_id), DTEventItemLottery.author_id == str(author_id), DTEventItemLottery.event_id == event_id))
  return result.scalar_one_or_none() is not None

async def create_event_item_lottery(author: disnake.Member, channel: Union[disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable],
                                    reward_item_g4: Optional[dt_items_repo.DTItem]=None, item_g4_amount: int=0,
                                    reward_item_g3: Optional[dt_items_repo.DTItem]=None, item_g3_amount: int=0,
                                    reward_item_g2: Optional[dt_items_repo.DTItem]=None, item_g2_amount: int=0,
                                    reward_item_g1: Optional[dt_items_repo.DTItem]=None, item_g1_amount: int=0) -> Optional[DTEventItemLottery]:
  year, week = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))
  event_specification = await event_participation_repo.get_or_create_event_specification(year, week)

  if await event_lotery_exist(author.guild.id, author.id, event_specification.event_id):
    return None

  await discord_objects_repo.get_or_create_discord_member(author, True)

  item = DTEventItemLottery(author_id=str(author.id), guild_id=str(author.guild.id), lottery_channel_id=str(channel.id), event_id=event_specification.event_id,
                            guessed_4_reward_item_name=reward_item_g4.name if reward_item_g4 is not None else None, guessed_4_item_reward_amount=item_g4_amount if reward_item_g4 is not None else 0,
                            guessed_3_reward_item_name=reward_item_g3.name if reward_item_g3 is not None else None, guessed_3_item_reward_amount=item_g3_amount if reward_item_g3 is not None else 0,
                            guessed_2_reward_item_name=reward_item_g2.name if reward_item_g2 is not None else None, guessed_2_item_reward_amount=item_g2_amount if reward_item_g2 is not None else 0,
                            guessed_1_reward_item_name=reward_item_g1.name if reward_item_g1 is not None else None, guessed_1_item_reward_amount=item_g1_amount if reward_item_g1 is not None else 0)
  await add_item(item)

  return item

async def get_active_lotteries(year: Optional[int] = None, week: Optional[int] = None) -> List[DTEventItemLottery]:
  if year is None or week is None:
    nyear, nweek = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))
    result = await run_query(select(DTEventItemLottery).join(event_participation_repo.EventSpecification).filter(and_(DTEventItemLottery.closed_at == None, or_(event_participation_repo.EventSpecification.event_year != nyear, event_participation_repo.EventSpecification.event_week != nweek))))
  else:
    result = await run_query(select(DTEventItemLottery).join(event_participation_repo.EventSpecification).filter(and_(DTEventItemLottery.closed_at == None, or_(event_participation_repo.EventSpecification.event_year == year, event_participation_repo.EventSpecification.event_week == week))))
  return result.scalars().all()

async def get_lotteries_in_guild(guild_id: int) -> List[DTEventItemLottery]:
  result = await run_query(select(DTEventItemLottery).filter(DTEventItemLottery.guild_id == str(guild_id)).order_by(DTEventItemLottery.created_at.desc()))
  return result.scalars().all()

async def get_lotteries_closed_before_date(date: datetime.datetime) -> List[DTEventItemLottery]:
  result = await run_query(select(DTEventItemLottery).filter(DTEventItemLottery.closed_at <= date))
  return result.scalars().all()

async def remove_lottery(id_:int) -> bool:
  result = await run_query(delete(DTEventItemLottery).filter(DTEventItemLottery.id == id_), commit=True)
  return result.rowcount > 0

async def get_guess(guild_id: int, author_id: int, event_id: int) -> Optional[DTEventItemLotteryGuess]:
  result = await run_query(select(DTEventItemLotteryGuess).filter(DTEventItemLotteryGuess.guild_id == str(guild_id), DTEventItemLotteryGuess.author_id == str(author_id), DTEventItemLotteryGuess.event_id == event_id))
  return result.scalar_one_or_none()

async def get_guesses(guild_id: int, event_id: int) -> List[DTEventItemLotteryGuess]:
  result = await run_query(select(DTEventItemLotteryGuess).filter(DTEventItemLotteryGuess.event_id == event_id, DTEventItemLotteryGuess.guild_id == str(guild_id)))
  return result.scalars().all()

async def remove_guess(guild_id: int, author_id: int, event_id: int) -> bool:
  result = await run_query(delete(DTEventItemLotteryGuess).filter(DTEventItemLotteryGuess.guild_id == str(guild_id), DTEventItemLotteryGuess.author_id == str(author_id), DTEventItemLotteryGuess.event_id == event_id))
  return result.rowcount > 0

async def make_next_event_guess(author: disnake.Member, items: List[dt_items_repo.DTItem]) -> Optional[DTEventItemLotteryGuess]:
  unique_item_names = list(set([item.name for item in items]))
  if len(unique_item_names) != len(items):
    return None

  year, week = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))
  event_specification = await event_participation_repo.get_or_create_event_specification(year, week)

  guess = await get_guess(author.guild.id, author.id, event_specification.event_id)

  if guess is not None:
    # Guess already made so remove old items
    await run_query(delete(DTEventItemLotteryGuessedItem).filter(DTEventItemLotteryGuessedItem.guess_id == guess.id), commit=True)
  else:
    await discord_objects_repo.get_or_create_discord_member(author, True)

    guess = DTEventItemLotteryGuess(guild_id=str(author.guild.id), author_id=str(author.id), event_id=event_specification.event_id)
    await add_item(guess)

  await add_items([DTEventItemLotteryGuessedItem(guess_id=guess.id, item_name=item.name) for item in items])

  return guess

async def clear_old_guesses() -> int:
  # This one should be enough for clearing all already processed quesses
  # Deletes all guesses that are connected to event that already have set items
  result = await run_query(text("""
    DELETE
    FROM dt_event_item_lottery_guesses
    WHERE event_id IN (
        SELECT DISTINCT event_id
        FROM event_items
        );
  """), commit=True)

  return result.rowcount

async def get_results(lottery: DTEventItemLottery) -> Tuple[int, Optional[Dict[int, List[discord_objects_repo.DiscordUser]]]]:
  """
  :param lottery: Lottery object
  :return: Tuple[number_of_guessers, Optional[Dict[number_of_right_guesses, List[DiscordUser]]]]
  """

  guesses = await get_guesses(int(lottery.guild_id), lottery.event_id)

  event_items = list(lottery.event_specification.participation_items)
  if not event_items:
    return len(guesses), None

  event_item_names = [ei.item_name for ei in event_items]
  event_item_names_set = set(event_item_names)

  results = {}
  for guess in guesses:
    guessed_items = list(guess.guessed_lotery_items)
    if not guessed_items: continue

    guessed_item_names = [gi.item_name for gi in guessed_items]

    guessed_right = len(event_item_names_set & set(guessed_item_names))
    if guessed_right == 0: continue

    if guessed_right not in results.keys():
      results[guessed_right] = [guess.member]
    else:
      results[guessed_right].append(guess.member)

  return len(guesses), results