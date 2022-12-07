import datetime
import statistics
from typing import Optional, List, Tuple, Any
from sqlalchemy import func

from database import session
from database.tables.event_participation import EventParticipation
from database.dt_guild_member_repo import get_and_update_dt_guild_members, create_dummy_dt_guild_member
from database import dt_user_repo, dt_guild_repo
from utils import dt_helpers


def get_event_participations(user_id: Optional[int] = None, guild_id: Optional[int] = None, year: Optional[int] = None, week: Optional[int] = None, order_by: Optional[List[Any]] = None, limit: int = 500) -> List[EventParticipation]:
  filters = []
  if order_by is None:
    order_by = [EventParticipation.event_year.desc(), EventParticipation.event_week.desc()]

  if user_id is not None:
    filters.append(EventParticipation.dt_user_id == user_id)
  if guild_id is not None:
    filters.append(EventParticipation.dt_guild_id == guild_id)
  if year is not None:
    filters.append(EventParticipation.event_year == year)
  if week is not None:
    filters.append(EventParticipation.event_week == week)

  return session.query(EventParticipation).filter(*filters).order_by(*order_by).limit(limit).all()


def get_best_participants(guild_id: Optional[int] = None, year: Optional[int] = None, week: Optional[int] = None, limit: int = 10, ignore_zero_participation_median: bool=False, ignore_zero_participation_average: bool=False) -> List[Tuple[int, str, int, str, int, float, float]]:
  """
  :param guild_id: Deep Town Guild ID
  :param year: Event year
  :param week: Event week
  :param limit: Limit of retrieved data rows
  :param ignore_zero_participation_median: Ignore zero participations for calculation of median
  :param ignore_zero_participation_average: Ignore zero participations for calculation of average
  :return: user id, username, guild id, guild name, total, average, median
  """
  filters = []
  if guild_id is not None:
    filters.append(EventParticipation.dt_guild_id == guild_id)
  if year is not None:
    filters.append(EventParticipation.event_year == year)
  if week is not None:
    filters.append(EventParticipation.event_week == week)

  data = session.query(
    dt_user_repo.DTUser.id,
    dt_user_repo.DTUser.username,
    dt_guild_repo.DTGuild.id,
    dt_guild_repo.DTGuild.name,
    func.sum(EventParticipation.amount),
    func.avg(EventParticipation.amount),
    func.percentile_cont(0.5).within_group(EventParticipation.amount))\
    .filter(*filters).join(dt_user_repo.DTUser, dt_guild_repo.DTGuild)\
    .group_by(dt_user_repo.DTUser.id, dt_user_repo.DTUser.username, dt_guild_repo.DTGuild.id, dt_guild_repo.DTGuild.name)\
    .order_by(func.sum(EventParticipation.amount).desc()).limit(limit).all()

  if ignore_zero_participation_average or ignore_zero_participation_median:
    output_data = []

    for user_id, username, guild_id, guild_name, total, average, median in data:
      additional_data = session.query(
        func.avg(EventParticipation.amount),
        func.percentile_cont(0.5).within_group(EventParticipation.amount))\
        .filter(*filters, EventParticipation.dt_user_id == user_id, EventParticipation.dt_guild_id == guild_id).one_or_none()

      ignore_zero_average, ignore_zero_median = 0, 0
      if all(additional_data):
        ignore_zero_average, ignore_zero_median = float(additional_data[0]), float(additional_data[1])

      output_data.append((user_id, username, guild_id, guild_name, total, ignore_zero_average if ignore_zero_participation_average else average, ignore_zero_median if ignore_zero_participation_median else median))

    return output_data
  return data


def get_guild_event_participations_data(guild_id: int, year: Optional[int] = None, week: Optional[int] = None, limit: int = 500, ignore_zero_participation_median: bool=False, ignore_zero_participation_average: bool=False) -> List[Tuple[int, int, int, float, float, int, int]]:
  """
  :param guild_id: Deep Town Guild ID
  :param year: Event year
  :param week: Event week
  :param limit: Limit of retrieved data rows
  :param ignore_zero_participation_median: Ignore zero participations for calculation of median
  :param ignore_zero_participation_average: Ignore zero participations for calculation of average
  :return: event_year, event_week, total, average, median, active_players, all_players
  """
  filters = [EventParticipation.dt_guild_id == guild_id]
  if year is not None:
    filters.append(EventParticipation.event_year == year)
  if week is not None:
    filters.append(EventParticipation.event_week == week)

  data = session.query(
      EventParticipation.event_year,
      EventParticipation.event_week,
      func.sum(EventParticipation.amount),
      func.avg(EventParticipation.amount),
      func.percentile_cont(0.5).within_group(EventParticipation.amount),
      func.count(func.nullif(EventParticipation.amount, 0)),
      func.count(EventParticipation.amount))\
      .filter(*filters)\
      .order_by(EventParticipation.event_year.desc(), EventParticipation.event_week.desc())\
      .group_by(EventParticipation.event_year, EventParticipation.event_week)\
      .limit(limit).all()

  if ignore_zero_participation_average or ignore_zero_participation_median:
    output_data = []

    for year, week, total, average, median, active_count, total_count in data:
      additional_data = session.query(
        func.avg(EventParticipation.amount),
        func.percentile_cont(0.5).within_group(EventParticipation.amount))\
        .filter(EventParticipation.dt_guild_id == guild_id, EventParticipation.event_year == year, EventParticipation.event_week == week, EventParticipation.amount > 0).one_or_none()

      ignore_zero_average, ignore_zero_median = 0, 0
      if all(additional_data):
        ignore_zero_average, ignore_zero_median = float(additional_data[0]), float(additional_data[1])

      output_data.append((year, week, total, ignore_zero_average if ignore_zero_participation_average else average, ignore_zero_median if ignore_zero_participation_median else median, active_count, total_count))

    return output_data
  return data

def get_recent_guild_event_participations(dt_guild_id: int) -> List[EventParticipation]:
  recent_year_results = session.query(func.max(EventParticipation.event_year)).one_or_none()
  if recent_year_results is None: return []
  recent_year = recent_year_results[0]

  recent_week_results = session.query(func.max(EventParticipation.event_week)).filter(EventParticipation.event_year == recent_year).one_or_none()
  if recent_week_results is None: return []
  recent_week = recent_week_results[0]

  return get_event_participations(guild_id=dt_guild_id, year=recent_year, week=recent_week, order_by=[EventParticipation.amount.desc()])


def get_and_update_event_participation(user_id: int, guild_id: int, event_year: int, event_week: int, participation_amount: int) -> EventParticipation:
  item = session.query(EventParticipation).filter(EventParticipation.event_year == event_year, EventParticipation.event_week == event_week, EventParticipation.dt_user_id == user_id, EventParticipation.dt_guild_id == guild_id).one_or_none()
  if item is None:
    create_dummy_dt_guild_member(user_id, guild_id)

    item = EventParticipation(event_year=event_year, event_week=event_week, dt_guild_id=guild_id, dt_user_id=user_id, amount=participation_amount)
    session.add(item)
  else:
    item.amount = participation_amount
  return item


def generate_or_update_event_participations(guild_data: dt_helpers.DTGuildData) -> List[EventParticipation]:
  get_and_update_dt_guild_members(guild_data)

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
    participations.append(get_and_update_event_participation(player_data.id, guild_data.id, event_year, event_week, player_data.last_event_contribution if updated else 0))
  session.commit()
  return participations


def dump_guild_event_participation_data(guild_id: Optional[int] = None) -> List[Tuple[int, int, int, str, int, str, int]]:
  filters = [EventParticipation.dt_guild_id == guild_id] if guild_id is not None else []
  data = session.query(
    EventParticipation.event_year,
    EventParticipation.event_week,
    EventParticipation.dt_guild_id,
    dt_guild_repo.DTGuild.name,
    EventParticipation.dt_user_id,
    dt_user_repo.DTUser.username,
    EventParticipation.amount
  ).join(dt_user_repo.DTUser).join(dt_guild_repo.DTGuild).filter(*filters).all()
  return data


def get_year_max_week(guild_id: int, event_year: int) -> Optional[int]:
  data = session.query(func.max(EventParticipation.event_week)).filter(EventParticipation.dt_guild_id == guild_id, EventParticipation.event_year == event_year).one_or_none()
  if data is None: return None
  return data[0]
