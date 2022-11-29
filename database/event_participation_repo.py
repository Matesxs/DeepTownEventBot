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
    players.append(dt_helpers.DTUserData(participation.dt_user.username, participation.dt_user.id, participation.dt_user.level, participation.dt_user.depth, participation.dt_user.last_online, participation.amount))

  return dt_helpers.DTGuildData(participations[0].dt_guild.name, participations[0].dt_guild.id, participations[0].dt_guild.level, players), participation.year, participation.event_week

def get_event_participation(user_id: int, guild_id: int, event_year: int, event_week: int) -> Optional[EventParticipation]:
  return session.query(EventParticipation).filter(EventParticipation.year == event_year, EventParticipation.event_week == event_week, EventParticipation.dt_user_id == user_id, EventParticipation.dt_guild_id == guild_id).one_or_none()

def get_participation_stats_for_guild_per_event(guild_id: int, year: int) -> List[Tuple[int, float, float]]:
  data = session.query(EventParticipation.event_week, func.avg(EventParticipation.amount), func.sum(EventParticipation.amount)).filter(EventParticipation.dt_guild_id == guild_id, EventParticipation.year == year).group_by(EventParticipation.event_week).all()
  output_data = []
  for d in data:
    output_data.append((d[0], float(d[1]), float(d[2])))
  return output_data

def get_participation_stats_for_guild_and_event(guild_id: int, year: int, week: int) -> Tuple[float, float]:
  result = session.query(func.avg(EventParticipation.amount), func.sum(EventParticipation.amount)).filter(EventParticipation.dt_guild_id == guild_id, EventParticipation.year == year, EventParticipation.event_week == week).one_or_none()
  if result: return float(result[0]), float(result[1])
  return 0, 0

def get_and_update_event_participation(user_id: int, guild_id: int, event_year: int, event_week: int, participation_amount: int):
  item = get_event_participation(user_id, guild_id, event_year, event_week)
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

  participations = []
  for player_data in guild_data.players:
    participations.append(get_and_update_event_participation(player_data.id, guild_data.id, event_year, event_week, player_data.last_event_contribution))
  session.commit()
  return participations

def get_recent_event_participation(dt_guild_id: int) -> List[EventParticipation]:
  recent_week = session.query(func.max(EventParticipation.event_week)).first()[0]
  recent_year = session.query(func.max(EventParticipation.year)).first()[0]
  return session.query(EventParticipation).filter(EventParticipation.year==recent_year,EventParticipation.event_week==recent_week, EventParticipation.dt_guild_id==dt_guild_id).all()
