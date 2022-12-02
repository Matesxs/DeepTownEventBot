from typing import Optional, List

from database import session
from database.tables.dt_guild_member import DTGuildMember
from database.dt_guild_repo import get_and_update_dt_guild, create_dummy_dt_guild
from database.dt_user_repo import get_and_update_dt_user, create_dummy_dt_user
from utils.dt_helpers import DTGuildData, DTUserData

def get_dt_guild_member(user_id: int, guild_id: int) -> Optional[DTGuildMember]:
  return session.query(DTGuildMember).filter(DTGuildMember.dt_user_id == user_id, DTGuildMember.dt_guild_id == guild_id).one_or_none()

def create_dummy_dt_guild_member(user_id: int, guild_id: int) -> DTGuildMember:
  item = get_dt_guild_member(user_id, guild_id)
  if item is None:
    create_dummy_dt_guild(guild_id)
    create_dummy_dt_user(user_id)

    item = DTGuildMember(dt_user_id=user_id, dt_guild_id=guild_id, current_member=False)
    session.add(item)
    session.commit()
  return item

def __get_and_update_dt_guild_member(user_data: DTUserData, guild_id: int) -> DTGuildMember:
  get_and_update_dt_user(user_data) # Always update DT user data

  item = get_dt_guild_member(user_data.id, guild_id)
  if item is None:
    item = DTGuildMember(dt_user_id=user_data.id, dt_guild_id=guild_id)
    session.add(item)
    session.commit()
  else:
    item.current_member = True

  session.query(DTGuildMember).filter(DTGuildMember.dt_user_id == user_data.id, DTGuildMember.dt_guild_id != guild_id).update({ "current_member": False })
  session.commit()

  return item

def get_and_update_dt_guild_members(guild_data: DTGuildData) -> List[DTGuildMember]:
  get_and_update_dt_guild(guild_data)

  dt_members = []
  for player_data in guild_data.players:
    dt_members.append(__get_and_update_dt_guild_member(player_data, guild_data.id))
  return dt_members
