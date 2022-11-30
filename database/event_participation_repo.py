import datetime
from typing import Optional, List, Tuple
from sqlalchemy import func

from database import session
from database.tables.event_participation import EventParticipation
from database.dt_guild_member_repo import get_and_update_dt_guild_members, create_dummy_dt_guild_member
from utils import dt_helpers

def event_list_participation_to_dt_guild_data(participations: List[EventParticipation]) -> Optional[Tuple[dt_helpers.DTGuildData, int, int]]:
  if not participations: return None

  players = []
  for participation in participations:
    players.append(participation.to_DTUserData())

  return dt_helpers.DTGuildData(participations[0].dt_guild.name, participations[0].dt_guild.id, participations[0].dt_guild.level, players), participation.year, participation.event_week

def get_user_event_participation(user_id: int, guild_id: int, event_year: int, event_week: int) -> Optional[EventParticipation]:
  return session.query(EventParticipation).filter(EventParticipation.year == event_year, EventParticipation.event_week == event_week, EventParticipation.dt_user_id == user_id, EventParticipation.dt_guild_id == guild_id).one_or_none()

def get_user_event_participations(user_id: int, guild_id: Optional[int]=None, year: Optional[int]=None, week: Optional[int]=None) -> List[EventParticipation]:
  filters = [EventParticipation.dt_user_id == user_id]
  if guild_id is not None:
    filters.append(EventParticipation.dt_guild_id == guild_id)
  if year is not None:
    filters.append(EventParticipation.year == year)
  if week is not None:
    filters.append(EventParticipation.event_week == week)

  return session.query(EventParticipation).filter(*filters).order_by(EventParticipation.year.desc(), EventParticipation.event_week.desc()).all()

def get_guild_event_participations(dt_guild_id: int, year: int, week: int) -> List[EventParticipation]:
  return session.query(EventParticipation).filter(EventParticipation.year==year,EventParticipation.event_week==week, EventParticipation.dt_guild_id==dt_guild_id).all()

def get_recent_event_participations(dt_guild_id: int) -> List[EventParticipation]:
  recent_week = session.query(func.max(EventParticipation.event_week)).first()[0]
  recent_year = session.query(func.max(EventParticipation.year)).first()[0]
  return get_guild_event_participations(dt_guild_id, recent_year, recent_week)

def get_and_update_event_participation(user_id: int, guild_id: int, event_year: int, event_week: int, participation_amount: int):
  item = get_user_event_participation(user_id, guild_id, event_year, event_week)
  if item is None:
    create_dummy_dt_guild_member(user_id, guild_id)

    item = EventParticipation(year=event_year, event_week=event_week, dt_guild_id=guild_id, dt_user_id=user_id, amount=participation_amount)
    session.add(item)
  else:
    item.amount = participation_amount
  return item

def generate_or_update_event_participations(guild_data: dt_helpers.DTGuildData) -> List[EventParticipation]:
  get_and_update_dt_guild_members(guild_data)

  event_year, event_week = dt_helpers.get_event_index(datetime.datetime.utcnow())
  prev_event_year, prev_event_week = dt_helpers.get_event_index(datetime.datetime.utcnow() - datetime.timedelta(days=7))

  participations = []
  for player_data in guild_data.players:
    prev_participation = get_user_event_participation(player_data.id, guild_data.id, prev_event_year, prev_event_week)

    contribution = player_data.last_event_contribution if prev_participation is None or prev_participation.amount != player_data.last_event_contribution else 0
    participations.append(get_and_update_event_participation(player_data.id, guild_data.id, event_year, event_week, contribution))
  session.commit()
  return participations
