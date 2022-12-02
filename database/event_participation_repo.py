import datetime
import statistics
from typing import Optional, List, Tuple
from sqlalchemy import func

from database import session
from database.tables.event_participation import EventParticipation
from database.dt_guild_member_repo import get_and_update_dt_guild_members, create_dummy_dt_guild_member
from database import dt_user_repo, dt_guild_repo
from utils import dt_helpers

def event_list_participation_to_dt_guild_data(participations: List[EventParticipation]) -> Optional[Tuple[dt_helpers.DTGuildData, int, int]]:
  if not participations: return None

  players = []
  for participation in participations:
    players.append(participation.to_DTUserData())

  return dt_helpers.DTGuildData(participations[0].dt_guild.name, participations[0].dt_guild.id, participations[0].dt_guild.level, players), participation.event_year, participation.event_week

def get_event_participations(user_id: Optional[int]=None, guild_id: Optional[int]=None, year: Optional[int]=None, week: Optional[int]=None) -> List[EventParticipation]:
  filters = []
  if user_id is not None:
    filters.append(EventParticipation.dt_user_id == user_id)
  if guild_id is not None:
    filters.append(EventParticipation.dt_guild_id == guild_id)
  if year is not None:
    filters.append(EventParticipation.event_year == year)
  if week is not None:
    filters.append(EventParticipation.event_week == week)

  return session.query(EventParticipation).filter(*filters).order_by(EventParticipation.event_year.desc(), EventParticipation.event_week.desc()).limit(500).all()

def get_best_participant(dt_guild_id: int, year: int, week: int) -> Optional[str]:
  data = session.query(dt_user_repo.DTUser.username).filter(EventParticipation.dt_guild_id == dt_guild_id, EventParticipation.event_year == year, EventParticipation.event_week == week).join(EventParticipation).order_by(EventParticipation.amount.desc()).first()
  if data is None: return None
  return data[0]

def get_guild_event_participations_data(dt_guild_id: int, year: Optional[int]=None, week: Optional[int]=None) -> List[Tuple[int, int, int, float]]:
  filters = [EventParticipation.dt_guild_id == dt_guild_id]
  if year is not None:
    filters.append(EventParticipation.event_year == year)
  if week is not None:
    filters.append(EventParticipation.event_week == week)
  return session.query(EventParticipation.event_year, EventParticipation.event_week, func.sum(EventParticipation.amount), func.avg(EventParticipation.amount)).filter(*filters).order_by(EventParticipation.event_year.desc(), EventParticipation.event_week.desc()).group_by(EventParticipation.event_year, EventParticipation.event_week).limit(500).all()

def get_recent_event_participations(dt_guild_id: int) -> List[EventParticipation]:
  recent_year_results = session.query(func.max(EventParticipation.event_year)).one_or_none()
  if recent_year_results is None: return []
  recent_year = recent_year_results[0]

  recent_week_results = session.query(func.max(EventParticipation.event_week)).filter(EventParticipation.event_year == recent_year).one_or_none()
  if recent_week_results is None: return []
  recent_week = recent_week_results[0]

  return session.query(EventParticipation).filter(EventParticipation.dt_guild_id == dt_guild_id, EventParticipation.event_year == recent_year, EventParticipation.event_week == recent_week).order_by(EventParticipation.amount.desc()).all()

def get_and_update_event_participation(user_id: int, guild_id: int, event_year: int, event_week: int, participation_amount: int) -> EventParticipation:
  item = session.query(EventParticipation).filter(EventParticipation.event_year == event_year, EventParticipation.event_week == event_week, EventParticipation.dt_user_id == user_id, EventParticipation.dt_guild_id == guild_id).one_or_none()
  if item is None:
    create_dummy_dt_guild_member(user_id, guild_id)

    item = EventParticipation(event_year=event_year, event_week=event_week, dt_guild_id=guild_id, dt_user_id=user_id, amount=participation_amount)
    session.add(item)
  else:
    item.amount = participation_amount
  return item

def dump_guild_event_participation_data(guild_id: Optional[int]=None) -> List[Tuple[int, int, int, str, int, str, int]]:
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

def get_year_max_week(guild_id: int, event_year: int) -> Optional[int]:
  data = session.query(func.max(EventParticipation.event_week)).filter(EventParticipation.dt_guild_id == guild_id, EventParticipation.event_year == event_year).one_or_none()
  if data is None: return None
  return data[0]
