import datetime
from typing import Optional, List
from sqlalchemy import func

from database import session
from database.tables.event_participation import EventParticipation
from database.dt_guild_member_repo import get_and_update_dt_guild_members
from utils import dt_helpers

def get_current_event_participation(user_id: int, guild_id: int) -> Optional[EventParticipation]:
  event_year, event_week = dt_helpers.get_event_index(datetime.datetime.utcnow())
  return session.query(EventParticipation).filter(EventParticipation.year == event_year, EventParticipation.event_week == event_week, EventParticipation.dt_user_id == user_id, EventParticipation.dt_guild_id == guild_id).one_or_none()

def __get_and_update_event_participation(user_id: int, guild_id: int, participation_amount: int):
  item = get_current_event_participation(user_id, guild_id)
  if item is None:
    event_year, event_week = dt_helpers.get_event_index(datetime.datetime.utcnow())
    item = EventParticipation(year=event_year, event_week=event_week, dt_guild_id=guild_id, dt_user_id=user_id, amount=participation_amount)
    session.add(item)
    session.commit()
  else:
    item.amount = participation_amount
  return item

def generate_or_update_event_participations(guild_data: dt_helpers.DTGuildData) -> List[EventParticipation]:
  get_and_update_dt_guild_members(guild_data)

  participations = []
  for player_data in guild_data.players:
    participations.append(__get_and_update_event_participation(player_data.id, guild_data.id, player_data.last_event_contribution))
  session.commit()
  return participations

def get_recent_event_participation(dt_guild_id: int) -> List[EventParticipation]:
  recent_week = session.query(func.max(EventParticipation.event_week)).first()[0]
  recent_year = session.query(func.max(EventParticipation.year)).first()[0]
  return session.query(EventParticipation).filter(EventParticipation.year==recent_year,EventParticipation.event_week==recent_week, EventParticipation.dt_guild_id==dt_guild_id).order_by(EventParticipation.amount.desc()).all()
