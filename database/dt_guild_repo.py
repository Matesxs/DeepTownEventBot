from typing import Optional, List

from database import session
from database.tables.dt_guild import DTGuild
from utils.dt_helpers import DTGuildData

def get_dt_guild(guild_id:int) -> Optional[DTGuild]:
  return session.query(DTGuild).filter(DTGuild.id == guild_id).one_or_none()

def create_dummy_dt_guild(id: int) -> DTGuild:
  item = get_dt_guild(id)
  if item is None:
    item = DTGuild(id=id, name="Unknown", level=-1)
    session.add(item)
    session.commit()
  return item

def get_and_update_dt_guild(guild_data: DTGuildData) -> DTGuild:
  item = get_dt_guild(guild_data.id)
  if item is None:
    item = DTGuild(id=guild_data.id, name=guild_data.name, level=guild_data.level)
    session.add(item)
  else:
    item.name = guild_data.name
    item.level = guild_data.level
  session.commit()
  return item

def remove_deleted_guilds(guild_id_list: List[int]) -> int:
  deleted_guilds = session.query(DTGuild).filter(DTGuild.id.not_in(guild_id_list)).delete()
  session.commit()
  return deleted_guilds
