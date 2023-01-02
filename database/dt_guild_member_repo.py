from typing import Optional, List
from sqlalchemy import func

from database import session
from database.tables.dt_guild_member import DTGuildMember
from database.dt_guild_repo import get_and_update_dt_guild, create_dummy_dt_guild
from database.dt_user_repo import get_and_update_dt_user, create_dummy_dt_user
from utils.dt_helpers import DTGuildData

def get_dt_guild_member(user_id: int, guild_id: int) -> Optional[DTGuildMember]:
  return session.query(DTGuildMember).filter(DTGuildMember.dt_user_id == user_id, DTGuildMember.dt_guild_id == guild_id).one_or_none()

def create_dummy_dt_guild_member(user_id: int, guild_id: int) -> Optional[DTGuildMember]:
  item = get_dt_guild_member(user_id, guild_id)
  if item is None:
    if create_dummy_dt_guild(guild_id) is None:
      return None

    if create_dummy_dt_user(user_id) is None:
      return None

    item = DTGuildMember(dt_user_id=user_id, dt_guild_id=guild_id, current_member=False)
    session.add(item)
    session.commit()
  return item

def get_and_update_dt_guild_members(guild_data: DTGuildData) -> Optional[List[DTGuildMember]]:
  if get_and_update_dt_guild(guild_data) is None:
    return None

  dt_members = []
  for player_data in guild_data.players:
    if get_and_update_dt_user(player_data) is None:
      continue

    item = get_dt_guild_member(player_data.id, guild_data.id)
    if item is None:
      item = DTGuildMember(dt_user_id=player_data.id, dt_guild_id=guild_data.id)
      session.add(item)
      session.commit()
    else:
      item.current_member = True

    session.query(DTGuildMember).filter(DTGuildMember.dt_user_id == player_data.id, DTGuildMember.dt_guild_id != guild_data.id).update({"current_member": False})
    session.commit()

    dt_members.append(item)
  return dt_members

def get_number_of_members(guild_id: int) -> int:
  data = session.query(func.count(DTGuildMember.dt_user_id)).filter(DTGuildMember.dt_guild_id == guild_id, DTGuildMember.current_member == True).one_or_none()
  return data[0] if data is not None else 0
