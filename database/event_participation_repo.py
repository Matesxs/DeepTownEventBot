import datetime
from typing import Optional, List, Tuple, Any
from sqlalchemy import func, and_, select, or_, text

from database import run_query_in_thread, run_commit_in_thread
from database.tables.event_participation import EventParticipation, EventSpecification
from database.dt_guild_member_repo import get_and_update_dt_guild_members, create_dummy_dt_guild_member
from database.dt_member_criteria import have_participation_elsewhere
from database import dt_user_repo, dt_guild_repo, dt_guild_member_repo
from utils import dt_helpers
from utils.logger import setup_custom_logger

logger = setup_custom_logger(__name__)

async def get_event_specification(session, year: int, week: int) -> Optional[EventSpecification]:
  result = await run_query_in_thread(session, select(EventSpecification).filter(EventSpecification.event_year == year, EventSpecification.event_week == week))
  return result.scalar_one_or_none()

async def get_or_create_event_specification(session, year: int, week: int) -> EventSpecification:
  item = await get_event_specification(session, year, week)
  if item is None:
    item = EventSpecification(event_year=year, event_week=week)
    session.add(item)
    await run_commit_in_thread(session)
  return item

async def get_event_participations(session, user_id: Optional[int] = None, guild_id: Optional[int] = None, year: Optional[int] = None, week: Optional[int] = None, order_by: Optional[List[Any]] = None, limit: int = 730) -> List[EventParticipation]:
  filters = []
  if order_by is None:
    order_by = [EventSpecification.event_year.desc(), EventSpecification.event_week.desc()]

  if user_id is not None:
    filters.append(EventParticipation.dt_user_id == user_id)
  if guild_id is not None:
    filters.append(EventParticipation.dt_guild_id == guild_id)
  if year is not None:
    filters.append(EventSpecification.event_year == year)
  if week is not None:
    filters.append(EventSpecification.event_week == week)

  result = await run_query_in_thread(session, select(EventParticipation).join(EventSpecification).filter(*filters).order_by(*order_by).limit(limit))
  return result.scalars().all()

async def get_event_participants_data(session, guild_id: Optional[int] = None, year: Optional[int] = None, week: Optional[int] = None, limit: int = 10, order_by: Optional[List[Any]]=None, ignore_zero_participation_median: bool=False, ignore_zero_participation_average: bool=False, only_current_members: bool=False) -> List[Tuple[int, str, int, str, int, float, float]]:
  """
  :param session: Database session
  :param guild_id: Deep Town Guild ID
  :param year: Event year
  :param week: Event week
  :param limit: Limit of retrieved data rows
  :param order_by: Order in which retrieve data
  :param ignore_zero_participation_median: Ignore zero participations for calculation of median
  :param ignore_zero_participation_average: Ignore zero participations for calculation of average
  :param only_current_members: Get stats only from current members
  :return: List[Tuple[user id, username, guild id, guild name, total, average, median]]
  """
  filters = []
  if guild_id is not None:
    filters.append(EventParticipation.dt_guild_id == guild_id)
  if year is not None:
    filters.append(EventSpecification.event_year == year)
  if week is not None:
    filters.append(EventSpecification.event_week == week)

  if order_by is None:
    order_by = [func.avg(EventParticipation.amount).desc()]

  data_query = select(dt_user_repo.DTUser.id, dt_user_repo.DTUser.username, dt_guild_repo.DTGuild.id, dt_guild_repo.DTGuild.name, func.sum(EventParticipation.amount), func.avg(EventParticipation.amount), func.percentile_cont(0.5).within_group(EventParticipation.amount))\
    .join(EventSpecification) \
    .join(dt_guild_repo.DTGuild) \
    .join(dt_user_repo.DTUser)

  if only_current_members:
    data_query = data_query.join(dt_guild_member_repo.DTGuildMember, and_(dt_guild_member_repo.DTGuildMember.dt_user_id == EventParticipation.dt_user_id, dt_guild_member_repo.DTGuildMember.dt_guild_id == dt_guild_repo.DTGuild.id))

  if filters:
    data_query = data_query.filter(*filters)

  data_query = data_query.group_by(dt_user_repo.DTUser.id, dt_user_repo.DTUser.username, dt_guild_repo.DTGuild.id, dt_guild_repo.DTGuild.name)\
    .order_by(*order_by)\
    .limit(limit)

  # print(data_query)
  data = (await run_query_in_thread(session, data_query)).all()

  if ignore_zero_participation_average or ignore_zero_participation_median:
    output_data = []

    for user_id, username, guild_id, guild_name, total, average, median in data:
      additional_data = (await run_query_in_thread(session, select(func.avg(EventParticipation.amount), func.percentile_cont(0.5).within_group(EventParticipation.amount))
        .filter(*filters, EventParticipation.dt_user_id == user_id, EventParticipation.dt_guild_id == guild_id, EventParticipation.amount > 0)))\
        .one()

      ignore_zero_average, ignore_zero_median = 0, 0
      if all(additional_data):
        ignore_zero_average, ignore_zero_median = float(additional_data[0]), float(additional_data[1])

      output_data.append((user_id, username, guild_id, guild_name, total, ignore_zero_average if ignore_zero_participation_average else average, ignore_zero_median if ignore_zero_participation_median else median))

    return output_data
  return [(d[0], d[1], d[2], d[3], d[4], d[5], d[6] if d[6] is not None else 0) for d in data]

async def get_users_leaderboard(session, year: int, week: int, limit: int = 10) -> List[Tuple[str, str, int]]:
  return ((await run_query_in_thread(session, select(dt_user_repo.DTUser.username, dt_guild_repo.DTGuild.name, func.sum(EventParticipation.amount))
                                             .select_from(EventParticipation)
                                             .join(EventSpecification)
                                             .join(dt_guild_repo.DTGuild)
                                             .join(dt_user_repo.DTUser)
                                             .filter(EventSpecification.event_year == year, EventSpecification.event_week == week)
                                             .group_by(dt_user_repo.DTUser.username, dt_guild_repo.DTGuild.name)
                                             .order_by(func.sum(EventParticipation.amount).desc())
                                             .limit(limit))).all())

async def get_guild_leaderbord(session, year: int, week: int, limit: int = 10) -> List[Tuple[str, int, int]]:
  return (await run_query_in_thread(session, select(dt_guild_repo.DTGuild.name, func.sum(EventParticipation.amount), func.max(EventParticipation.amount))
                                             .select_from(EventParticipation)
                                             .join(EventSpecification)
                                             .join(dt_guild_repo.DTGuild)
                                             .filter(EventSpecification.event_year == year, EventSpecification.event_week == week)
                                             .group_by(dt_guild_repo.DTGuild.name)
                                             .order_by(func.sum(EventParticipation.amount).desc())
                                             .limit(limit))).all()

async def get_event_participation_stats(session, guild_id: Optional[int]=None, user_id: Optional[int]=None, year: Optional[int]=None, ignore_zero_participation_median: bool=False, ignore_zero_participation_average: bool=False) -> Tuple[int, float, float]:
  """
  :param session: Database session
  :param guild_id: Deep Town Guild ID
  :param user_id: Deep Town User ID
  :param year: Event year
  :param ignore_zero_participation_median: Ignore zero participations for calculation of median
  :param ignore_zero_participation_average: Ignore zero participations for calculation of average
  :return: total, average, median
  """

  filters = []
  if guild_id is not None:
    filters.append(EventParticipation.dt_guild_id == guild_id)
  if user_id is not None:
    filters.append(EventParticipation.dt_user_id == user_id)
  if year is not None:
    filters.append(EventSpecification.event_year == year)

  distinc_amount_query = select(func.sum(EventParticipation.amount).label("amount"))\
                         .join(EventSpecification)\
                         .filter(*filters)\
                         .group_by(EventSpecification.event_year, EventSpecification.event_week)\
                         .subquery()

  data = (await run_query_in_thread(session, select(func.sum(distinc_amount_query.c.amount), func.avg(distinc_amount_query.c.amount), func.percentile_cont(0.5).within_group(distinc_amount_query.c.amount)))).one()
  if data[0] is None and data[1] is None and data[2] is None:
    return 0, 0, 0

  if ignore_zero_participation_average or ignore_zero_participation_median:
    additional_data = (await run_query_in_thread(session, select(func.avg(distinc_amount_query.c.amount), func.percentile_cont(0.5).within_group(distinc_amount_query.c.amount))
                                                          .filter(distinc_amount_query.c.amount > 0))).one()

    if not all(additional_data):
      additional_data = 0, 0

    median = additional_data[1] if ignore_zero_participation_median else data[2]
    return data[0], additional_data[0] if ignore_zero_participation_average else data[1], median if median is not None else 0
  return data[0], data[1], data[2] if data[2] is not None else 0

async def get_guild_event_participations_data(session, guild_id: int, year: Optional[int] = None, week: Optional[int] = None, limit: int = 730, ignore_zero_participation_average: bool=False) -> List[Tuple[int, int, int, float]]:
  """
  :param session: Database session
  :param guild_id: Deep Town Guild ID
  :param year: Event year
  :param week: Event week
  :param limit: Limit of retrieved data rows
  :param ignore_zero_participation_average: Ignore zero participations for calculation of average
  :return: List[Tuple[event_year, event_week, total, average]]
  """
  filters = [EventParticipation.dt_guild_id == guild_id]
  if year is not None:
    filters.append(EventSpecification.event_year == year)
  if week is not None:
    filters.append(EventSpecification.event_week == week)
  if ignore_zero_participation_average:
    filters.append(EventParticipation.amount > 0)

  data = (await run_query_in_thread(session, select(EventSpecification.event_year, EventSpecification.event_week, func.sum(EventParticipation.amount), func.avg(EventParticipation.amount))
                                             .join(EventParticipation)
                                             .filter(*filters)
                                             .order_by(EventSpecification.event_year.desc(), EventSpecification.event_week.desc())
                                             .group_by(EventSpecification.event_year, EventSpecification.event_week)
                                             .limit(limit))).all()
  return [(d[0], d[1], d[2], d[3]) for d in data]

async def get_event_participation(session, user_id: int, guild_id: int, event_year: int, event_week: int) -> Optional[EventParticipation]:
  result = await run_query_in_thread(session, select(EventParticipation).filter(EventSpecification.event_year == event_year, EventSpecification.event_week == event_week, EventParticipation.dt_user_id == user_id, EventParticipation.dt_guild_id == guild_id).join(EventSpecification))
  return result.scalar_one_or_none()

async def remove_event_participations(session, guild_id: int, event_year: int, event_week: int, user_id_filter: Optional[List[int]] = None):
  if user_id_filter is None or not user_id_filter:
    await run_query_in_thread(session, text(f"""
      DELETE
      FROM event_participations
      WHERE dt_guild_id = {guild_id} AND event_id IN (
          SELECT event_id
          FROM event_specifications
          WHERE event_year = {event_year} AND event_week = {event_week}
          );
    """), commit=True)
  else:
    filter_string = ",".join([str(i) for i in user_id_filter])
    await run_query_in_thread(session, text(f"""
      DELETE
      FROM event_participations
      WHERE dt_guild_id = {guild_id} AND dt_user_id NOT IN ({filter_string}) AND event_id IN (
          SELECT event_id
          FROM event_specifications
          WHERE event_year = {event_year} AND event_week = {event_week}
          );
    """), commit=True)

async def get_and_update_event_participation(session, user_id: int, guild_id: int, event_year: int, event_week: int, participation_amount: int) -> Optional[EventParticipation]:
  item = await get_event_participation(session, user_id, guild_id, event_year, event_week)
  if item is None:
    # If user have participation somewhere else (changed guild), skip him
    if await have_participation_elsewhere(session, user_id, guild_id, event_year, event_week, participation_amount):
      # logger.info(f"Skipped creation of participation in {event_year} {event_week} for user {user_id} in guild {guild_id}")
      return None

    if (await create_dummy_dt_guild_member(session, user_id, guild_id)) is None:
      return None

    specification = await get_or_create_event_specification(session, event_year, event_week)

    item = EventParticipation(event_id=specification.event_id, dt_guild_id=guild_id, dt_user_id=user_id, amount=participation_amount)
    session.add(item)
    await run_commit_in_thread(session)
  else:
    item.amount = participation_amount

  return item

async def generate_or_update_event_participations(session, guild_data: dt_helpers.DTGuildData) -> Optional[List[EventParticipation]]:
  event_year, event_week = dt_helpers.get_event_index(datetime.datetime.now(datetime.UTC))
  prev_event_year, prev_event_week = dt_helpers.get_event_index(datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=7))

  if (await get_and_update_dt_guild_members(session, guild_data, event_year, event_week)) is None:
    return None

  participation_amounts = [p.last_event_contribution for p in guild_data.players]
  prev_event_participations = await get_event_participations(session, guild_id=guild_data.id, year=prev_event_year, week=prev_event_week)
  prev_participation_amounts = [p.amount for p in prev_event_participations]

  new_event_started = True
  if prev_participation_amounts and participation_amounts and \
      sum(participation_amounts) == sum(prev_participation_amounts):
    new_event_started = False

  # Remove all participations from users that were currently not in guild
  await remove_event_participations(session, guild_data.id, event_year, event_week, [player_data.id for player_data in guild_data.players])

  participations = []
  for player_data in guild_data.players:
    participation = await get_and_update_event_participation(session, player_data.id, guild_data.id, event_year, event_week, player_data.last_event_contribution if new_event_started else 0)
    if participation is not None:
      participations.append(participation)

  await run_commit_in_thread(session)
  return participations

async def search_event_identificator(session, search: Optional[str]=None, limit: int=25) -> List[Tuple[int, int]]:
  """
  :param session: Database session
  :param search: Search phrase
  :param limit: Number of results
  :return: Tuple[year, week]
  """

  if search is None:
    result = await run_query_in_thread(session, select(EventSpecification.event_year, EventSpecification.event_week).order_by(EventSpecification.event_year.desc(), EventSpecification.event_week.desc()).limit(limit))
  else:
    search_parts = search.split(" ")
    search_parts = [int(p) for p in search_parts if p.isnumeric()]
    number_of_parts = len(search_parts)

    if number_of_parts == 0:
      result = await run_query_in_thread(session, select(EventSpecification.event_year, EventSpecification.event_week).order_by(EventSpecification.event_year.desc(), EventSpecification.event_week.desc()).limit(limit))
    elif number_of_parts == 1:
      result = await run_query_in_thread(session, select(EventSpecification.event_year, EventSpecification.event_week)
                                                  .filter(or_(EventSpecification.event_year == search_parts[0], EventSpecification.event_week == search_parts[0]))
                                                  .order_by(EventSpecification.event_year.desc(), EventSpecification.event_week.desc())
                                                  .limit(limit))
    else:
      result = await run_query_in_thread(session, select(EventSpecification.event_year, EventSpecification.event_week)
                                                  .filter(or_(and_(EventSpecification.event_year == search_parts[0], EventSpecification.event_week == search_parts[1]),
                                                              and_(EventSpecification.event_year == search_parts[1], EventSpecification.event_week == search_parts[0])))
                                                  .order_by(EventSpecification.event_year.desc(), EventSpecification.event_week.desc())
                                                  .limit(limit))

  return result.all()

async def search_event_year(session, search: Optional[str]=None, limit: int=25) -> List[int]:
  """
  :param session: Database session
  :param search: Search phrase
  :param limit: Number of results
  :return: list of years
  """

  if search is None or search == "" or not search.isnumeric():
    result = await run_query_in_thread(session, select(EventSpecification.event_year.distinct()).order_by(EventSpecification.event_year.desc()).limit(limit))
  else:
    result = await run_query_in_thread(session, select(EventSpecification.event_year.distinct()).filter(EventSpecification.event_year == int(search)).order_by(EventSpecification.event_year.desc()).limit(limit))
  return result.scalars().all()