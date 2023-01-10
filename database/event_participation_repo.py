import datetime
import statistics
from typing import Optional, List, Tuple, Any
from sqlalchemy import func, and_

from database import session
from database.tables.event_participation import EventParticipation, EventSpecification
from database.dt_guild_member_repo import get_and_update_dt_guild_members, create_dummy_dt_guild_member
from database import dt_user_repo, dt_guild_repo, dt_guild_member_repo
from utils import dt_helpers

def get_event_specification(year: int, week: int) -> Optional[EventSpecification]:
  return session.query(EventSpecification).filter(EventSpecification.event_year == year, EventSpecification.event_week == week).one_or_none()

def get_or_create_event_specification(year: int, week: int) -> EventSpecification:
  item = get_event_specification(year, week)
  if item is None:
    item = EventSpecification(event_year=year, event_week=week)
    session.add(item)
    session.commit()
  return item

def get_event_participations(user_id: Optional[int] = None, guild_id: Optional[int] = None, year: Optional[int] = None, week: Optional[int] = None, order_by: Optional[List[Any]] = None, limit: int = 500) -> List[EventParticipation]:
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

  return session.query(EventParticipation).join(EventSpecification).filter(*filters).order_by(*order_by).limit(limit).all()

def get_event_participants_data(guild_id: Optional[int] = None, year: Optional[int] = None, week: Optional[int] = None, limit: int = 10, order_by: Optional[List[Any]]=None, ignore_zero_participation_median: bool=False, ignore_zero_participation_average: bool=False, only_current_members: bool=False) -> List[Tuple[int, str, int, str, int, float, float]]:
  """
  :param guild_id: Deep Town Guild ID
  :param year: Event year
  :param week: Event week
  :param limit: Limit of retrieved data rows
  :param order_by: Order in which retrieve data
  :param ignore_zero_participation_median: Ignore zero participations for calculation of median
  :param ignore_zero_participation_average: Ignore zero participations for calculation of average
  :param only_current_members: Get stats only from current members
  :return: user id, username, guild id, guild name, total, average, median
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

  data_query = session.query(
    dt_user_repo.DTUser.id,
    dt_user_repo.DTUser.username,
    dt_guild_repo.DTGuild.id,
    dt_guild_repo.DTGuild.name,
    func.sum(EventParticipation.amount),
    func.avg(EventParticipation.amount),
    func.percentile_cont(0.5).within_group(EventParticipation.amount))\
    .join(EventSpecification) \
    .join(dt_guild_repo.DTGuild)\
    .join(dt_guild_member_repo.DTGuildMember, and_(dt_guild_member_repo.DTGuildMember.dt_user_id == EventParticipation.dt_user_id, dt_guild_member_repo.DTGuildMember.dt_guild_id == dt_guild_repo.DTGuild.id)) \
    .join(dt_user_repo.DTUser)\
    .filter(*filters, *([dt_guild_member_repo.DTGuildMember.current_member == True] if only_current_members else []))\
    .group_by(dt_user_repo.DTUser.id, dt_user_repo.DTUser.username, dt_guild_repo.DTGuild.id, dt_guild_repo.DTGuild.name)\
    .order_by(*order_by).limit(limit)

  # print(data_query)
  data = data_query.all()

  if ignore_zero_participation_average or ignore_zero_participation_median:
    output_data = []

    for user_id, username, guild_id, guild_name, total, average, median in data:
      additional_data = session.query(
        func.avg(EventParticipation.amount),
        func.percentile_cont(0.5).within_group(EventParticipation.amount))\
        .filter(*filters, EventParticipation.dt_user_id == user_id, EventParticipation.dt_guild_id == guild_id, EventParticipation.amount > 0).one_or_none()

      ignore_zero_average, ignore_zero_median = 0, 0
      if all(additional_data):
        ignore_zero_average, ignore_zero_median = float(additional_data[0]), float(additional_data[1])

      output_data.append((user_id, username, guild_id, guild_name, total, ignore_zero_average if ignore_zero_participation_average else average, ignore_zero_median if ignore_zero_participation_median else median))

    return output_data
  return data[0], data[1], data[2], data[3], data[4], data[5], data[6] if data[6] is not None else 0

def get_event_participation_stats(guild_id: Optional[int]=None, user_id: Optional[int]=None, year: Optional[int]=None, ignore_zero_participation_median: bool=False, ignore_zero_participation_average: bool=False) -> Tuple[int, float, float]:
  """
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

  data = session.query(
    func.sum(EventParticipation.amount),
    func.avg(EventParticipation.amount),
    func.percentile_cont(0.5).within_group(EventParticipation.amount)
  )\
    .join(EventSpecification)\
    .filter(*filters)\
    .one()

  if ignore_zero_participation_average or ignore_zero_participation_median:
    additional_data = session.query(
      func.avg(EventParticipation.amount),
      func.percentile_cont(0.5).within_group(EventParticipation.amount)
    ) \
      .join(EventSpecification) \
      .filter(*filters, EventParticipation.amount > 0) \
      .one()

    if not all(additional_data):
      additional_data = 0, 0

    median = additional_data[1] if ignore_zero_participation_median else data[2]
    return data[0], additional_data[0] if ignore_zero_participation_average else data[1], median if median is not None else 0
  return data[0], data[1], data[2] if data[2] is not None else 0

def get_guild_event_participations_data(guild_id: int, year: Optional[int] = None, week: Optional[int] = None, limit: int = 500, ignore_zero_participation_median: bool=False, ignore_zero_participation_average: bool=False) -> List[Tuple[int, int, int, float, float]]:
  """
  :param guild_id: Deep Town Guild ID
  :param year: Event year
  :param week: Event week
  :param limit: Limit of retrieved data rows
  :param ignore_zero_participation_median: Ignore zero participations for calculation of median
  :param ignore_zero_participation_average: Ignore zero participations for calculation of average
  :return: event_year, event_week, total, average, median
  """
  filters = [EventParticipation.dt_guild_id == guild_id]
  if year is not None:
    filters.append(EventSpecification.event_year == year)
  if week is not None:
    filters.append(EventSpecification.event_week == week)

  data = session.query(
      EventSpecification.event_year,
      EventSpecification.event_week,
      func.sum(EventParticipation.amount),
      func.avg(EventParticipation.amount),
      func.percentile_cont(0.5).within_group(EventParticipation.amount))\
      .join(EventParticipation)\
      .filter(*filters)\
      .order_by(EventSpecification.event_year.desc(), EventSpecification.event_week.desc())\
      .group_by(EventSpecification.event_year, EventSpecification.event_week)\
      .limit(limit).all()

  if ignore_zero_participation_average or ignore_zero_participation_median:
    output_data = []

    for year, week, total, average, median in data:
      additional_data = session.query(
        func.avg(EventParticipation.amount),
        func.percentile_cont(0.5).within_group(EventParticipation.amount))\
        .join(EventSpecification)\
        .filter(EventParticipation.dt_guild_id == guild_id, EventSpecification.event_year == year, EventSpecification.event_week == week, EventParticipation.amount > 0).one_or_none()

      ignore_zero_average, ignore_zero_median = 0, 0
      if all(additional_data):
        ignore_zero_average, ignore_zero_median = float(additional_data[0]), float(additional_data[1])

      output_data.append((year, week, total, ignore_zero_average if ignore_zero_participation_average else average, ignore_zero_median if ignore_zero_participation_median else median))

    return output_data
  return data[0], data[1], data[2], data[3], data[4] if data[4] is not None else 0

def get_and_update_event_participation(user_id: int, guild_id: int, event_year: int, event_week: int, participation_amount: int) -> Optional[EventParticipation]:
  item = session.query(EventParticipation).filter(EventSpecification.event_year == event_year, EventSpecification.event_week == event_week, EventParticipation.dt_user_id == user_id, EventParticipation.dt_guild_id == guild_id).join(EventSpecification).one_or_none()
  if item is None:
    if create_dummy_dt_guild_member(user_id, guild_id) is None:
      return None

    specification = get_or_create_event_specification(event_year, event_week)

    item = EventParticipation(event_id=specification.event_id, dt_guild_id=guild_id, dt_user_id=user_id, amount=participation_amount)
    session.add(item)
  else:
    item.amount = participation_amount
  return item


def generate_or_update_event_participations(guild_data: dt_helpers.DTGuildData) -> Optional[List[EventParticipation]]:
  if get_and_update_dt_guild_members(guild_data) is None:
    return None

  event_year, event_week = dt_helpers.get_event_index(datetime.datetime.utcnow())
  prev_event_year, prev_event_week = dt_helpers.get_event_index(datetime.datetime.utcnow() - datetime.timedelta(days=7))

  participation_amounts = [p.last_event_contribution for p in guild_data.players]
  prev_participation_amounts = [p.amount for p in get_event_participations(guild_id=guild_data.id, year=prev_event_year, week=prev_event_week)]

  updated = True
  if prev_participation_amounts and participation_amounts and \
      sum(participation_amounts) == sum(prev_participation_amounts) and \
      statistics.mean(participation_amounts) == statistics.mean(prev_participation_amounts) and \
      statistics.median(participation_amounts) == statistics.median(prev_participation_amounts):
    updated = False

  participations = []
  for player_data in guild_data.players:
    participation = get_and_update_event_participation(player_data.id, guild_data.id, event_year, event_week, player_data.last_event_contribution if updated else 0)
    if participation is not None:
      participations.append(participation)
  session.commit()
  return participations


def dump_guild_event_participation_data(guild_id: Optional[int] = None) -> List[Tuple[int, int, int, str, int, str, int]]:
  filters = [EventParticipation.dt_guild_id == guild_id] if guild_id is not None else []
  data = session.query(
    EventSpecification.event_year,
    EventSpecification.event_week,
    EventParticipation.dt_guild_id,
    dt_guild_repo.DTGuild.name,
    EventParticipation.dt_user_id,
    dt_user_repo.DTUser.username,
    EventParticipation.amount
  )\
    .select_from(EventSpecification)\
    .join(EventParticipation)\
    .join(dt_user_repo.DTUser)\
    .join(dt_guild_repo.DTGuild)\
    .filter(*filters).all()
  return data


def get_year_max_week(guild_id: int, event_year: int) -> Optional[int]:
  data = session.query(func.max(EventSpecification.event_week)).join(EventParticipation).filter(EventParticipation.dt_guild_id == guild_id, EventSpecification.event_year == event_year).one_or_none()
  if data is None: return None
  return data[0]
