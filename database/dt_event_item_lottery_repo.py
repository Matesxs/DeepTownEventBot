import datetime
import disnake
from sqlalchemy import select, delete, or_, and_, text
from typing import Optional, List, Dict, Union, Tuple

from database import run_query_in_thread, run_commit_in_thread, add_items, dt_items_repo, discord_objects_repo, event_participation_repo
from database.tables.dt_event_item_lottery import DTEventItemLottery, DTEventItemLotteryGuess, DTEventItemLotteryGuessedItem
from utils import dt_helpers

async def get_event_item_lottery(session, id_: int) -> Optional[DTEventItemLottery]:
  result = await run_query_in_thread(session, select(DTEventItemLottery).filter(DTEventItemLottery.id == id_))
  return result.scalar_one_or_none()

async def get_event_item_lottery_by_constrained(session, author_id: int, guild_id: int, event_id: int) -> Optional[DTEventItemLottery]:
  result = await run_query_in_thread(session, select(DTEventItemLottery).filter(DTEventItemLottery.author_id == str(author_id), DTEventItemLottery.guild_id == str(guild_id), DTEventItemLottery.event_id == event_id))
  return result.scalar_one_or_none()

async def get_next_event_item_lottery_by_constrained(session, author_id: int, guild_id: int) -> Optional[DTEventItemLottery]:
  next_year, next_week = dt_helpers.get_event_index(datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(days=7))
  event_specification = await event_participation_repo.get_or_create_event_specification(session, next_year, next_week)
  return await get_event_item_lottery_by_constrained(session, author_id, guild_id, event_specification.event_id)

async def event_lotery_exist(session, guild_id: int, author_id: int, event_id: int) -> bool:
  result = await run_query_in_thread(session, select(DTEventItemLottery.id).filter(DTEventItemLottery.guild_id == str(guild_id), DTEventItemLottery.author_id == str(author_id), DTEventItemLottery.event_id == event_id))
  return result.scalar_one_or_none() is not None

async def create_event_item_lottery(session, author: disnake.Member, channel: Union[disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable],
                                    reward_item_g4: Optional[dt_items_repo.DTItem]=None, item_g4_amount: int=0,
                                    reward_item_g3: Optional[dt_items_repo.DTItem]=None, item_g3_amount: int=0,
                                    reward_item_g2: Optional[dt_items_repo.DTItem]=None, item_g2_amount: int=0,
                                    reward_item_g1: Optional[dt_items_repo.DTItem]=None, item_g1_amount: int=0) -> Optional[DTEventItemLottery]:
  year, week = dt_helpers.get_event_index(datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(days=7))
  event_specification = await event_participation_repo.get_or_create_event_specification(session, year, week)

  if await event_lotery_exist(session, author.guild.id, author.id, event_specification.event_id):
    return None

  await discord_objects_repo.get_or_create_discord_member(session, author, True)

  item = DTEventItemLottery(author_id=str(author.id), guild_id=str(author.guild.id), lottery_channel_id=str(channel.id), event_id=event_specification.event_id,
                            guessed_4_reward_item_name=reward_item_g4.name if reward_item_g4 is not None else None, guessed_4_item_reward_amount=item_g4_amount if reward_item_g4 is not None else 0,
                            guessed_3_reward_item_name=reward_item_g3.name if reward_item_g3 is not None else None, guessed_3_item_reward_amount=item_g3_amount if reward_item_g3 is not None else 0,
                            guessed_2_reward_item_name=reward_item_g2.name if reward_item_g2 is not None else None, guessed_2_item_reward_amount=item_g2_amount if reward_item_g2 is not None else 0,
                            guessed_1_reward_item_name=reward_item_g1.name if reward_item_g1 is not None else None, guessed_1_item_reward_amount=item_g1_amount if reward_item_g1 is not None else 0)
  session.add(item)
  await run_commit_in_thread(session)

  return item

async def get_active_lotteries(session, year: Optional[int] = None, week: Optional[int] = None) -> List[DTEventItemLottery]:
  if year is None or week is None:
    nyear, nweek = dt_helpers.get_event_index(datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(days=7))
    result = await run_query_in_thread(session, select(DTEventItemLottery).join(event_participation_repo.EventSpecification).filter(and_(DTEventItemLottery.closed_at == None, or_(event_participation_repo.EventSpecification.event_year != nyear, event_participation_repo.EventSpecification.event_week != nweek))))
  else:
    result = await run_query_in_thread(session, select(DTEventItemLottery).join(event_participation_repo.EventSpecification).filter(and_(DTEventItemLottery.closed_at == None, or_(event_participation_repo.EventSpecification.event_year == year, event_participation_repo.EventSpecification.event_week == week))))
  return result.scalars().all()

async def get_lotteries_in_guild(session, guild_id: int) -> List[DTEventItemLottery]:
  result = await run_query_in_thread(session, select(DTEventItemLottery).filter(DTEventItemLottery.guild_id == str(guild_id)).order_by(DTEventItemLottery.created_at.desc()))
  return result.scalars().all()

async def get_lotteries_closed_before_date(session, date: datetime.datetime) -> List[DTEventItemLottery]:
  result = await run_query_in_thread(session, select(DTEventItemLottery).filter(DTEventItemLottery.closed_at <= date))
  return result.scalars().all()

async def get_guess(session, guild_id: int, author_id: int, event_id: int) -> Optional[DTEventItemLotteryGuess]:
  result = await run_query_in_thread(session, select(DTEventItemLotteryGuess).filter(DTEventItemLotteryGuess.guild_id == str(guild_id), DTEventItemLotteryGuess.author_id == str(author_id), DTEventItemLotteryGuess.event_id == event_id))
  return result.scalar_one_or_none()

async def get_guesses(session, guild_id: int, event_id: int) -> List[DTEventItemLotteryGuess]:
  result = await run_query_in_thread(session, select(DTEventItemLotteryGuess).filter(DTEventItemLotteryGuess.event_id == event_id, DTEventItemLotteryGuess.guild_id == str(guild_id)))
  return result.scalars().all()

async def remove_guess(session, guild_id: int, author_id: int, event_id: int) -> bool:
  result = await run_query_in_thread(session, delete(DTEventItemLotteryGuess).filter(DTEventItemLotteryGuess.guild_id == str(guild_id), DTEventItemLotteryGuess.author_id == str(author_id), DTEventItemLotteryGuess.event_id == event_id))
  return result.rowcount > 0

async def make_next_event_guess(session, author: disnake.Member, items: List[dt_items_repo.DTItem]) -> Optional[DTEventItemLotteryGuess]:
  unique_item_names = list(set([item.name for item in items]))
  if len(unique_item_names) != len(items):
    return None

  year, week = dt_helpers.get_event_index(datetime.datetime.now(datetime.UTC).replace(tzinfo=None) + datetime.timedelta(days=7))
  event_specification = await event_participation_repo.get_or_create_event_specification(session, year, week)

  guess = await get_guess(session, author.guild.id, author.id, event_specification.event_id)

  if guess is not None:
    # Guess already made so remove old items
    await run_query_in_thread(session, delete(DTEventItemLotteryGuessedItem).filter(DTEventItemLotteryGuessedItem.guess_id == guess.id), commit=True)
  else:
    await discord_objects_repo.get_or_create_discord_member(session, author, True)

    guess = DTEventItemLotteryGuess(guild_id=str(author.guild.id), author_id=str(author.id), event_id=event_specification.event_id)
    session.add(guess)
    await run_commit_in_thread(session)

  await add_items(session, [DTEventItemLotteryGuessedItem(guess_id=guess.id, item_name=item.name) for item in items])

  return guess

async def clear_old_guesses(session) -> int:
  # This one should be enough for clearing all already processed quesses
  # Deletes all guesses that are connected to event that already have set items
  result = await run_query_in_thread(session, text("""
    DELETE
    FROM dt_event_item_lottery_guesses
    WHERE event_id IN (
        SELECT DISTINCT event_id
        FROM event_items
        );
  """), commit=True)

  return result.rowcount

async def get_results(session, lottery: DTEventItemLottery) -> Optional[Tuple[int, Dict[int, List[discord_objects_repo.DiscordUser | discord_objects_repo.DiscordMember]]]]:
  """
  :param session: Database session
  :param lottery: Lottery object
  :return: Tuple[number_of_guessers, Dict[number_of_right_guesses, List[DiscordUser | DiscordMember]]]
  """

  guesses = await get_guesses(session, int(lottery.guild_id), lottery.event_id)

  event_items = list(lottery.event_specification.participation_items)
  if not event_items:
    return None

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
      results[guessed_right] = [guess.member or guess.user]
    else:
      results[guessed_right].append(guess.member or guess.user)

  return len(guesses), results