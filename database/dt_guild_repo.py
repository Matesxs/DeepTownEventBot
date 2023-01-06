from typing import Optional, List, Tuple
from sqlalchemy import or_

from database import session
from database.tables.dt_guild import DTGuild
from database import dt_blacklist_repo
from utils.dt_helpers import DTGuildData

def get_dt_guild(guild_id:int) -> Optional[DTGuild]:
  return session.query(DTGuild).filter(DTGuild.id == guild_id).one_or_none()

def get_all_guilds(search: Optional[str]=None, limit: int=25) -> List[DTGuild]:
  if search is not None:
    if search.isnumeric():
      return session.query(DTGuild).filter(or_(DTGuild.name.ilike(f"%{search}%"), DTGuild.id == int(search))).limit(limit).all()
    else:
      return session.query(DTGuild).filter(DTGuild.name.ilike(f"%{search}%")).limit(limit).all()
  return session.query(DTGuild).limit(limit).all()

def get_dt_guilds_by_identifier(identifier: str) -> List[DTGuild]:
  if identifier.isnumeric():
    result = get_dt_guild(int(identifier))
    if result is not None:
      return [result]

  return session.query(DTGuild).filter(DTGuild.name == identifier).all()

def create_dummy_dt_guild(id: int) -> Optional[DTGuild]:
  item = get_dt_guild(id)
  if item is None:
    if dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.GUILD, id):
      return None

    item = DTGuild(id=id, name="Unknown", level=-1)
    session.add(item)
    session.commit()
  return item

def get_and_update_dt_guild(guild_data: DTGuildData) -> Optional[DTGuild]:
  item = get_dt_guild(guild_data.id)
  if item is None:
    if dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.GUILD, guild_data.id):
      return None

    item = DTGuild(id=guild_data.id, name=guild_data.name, level=guild_data.level)
    session.add(item)
  else:
    item.name = guild_data.name
    item.level = guild_data.level
  session.commit()
  return item

def remove_guild(id: int) -> bool:
  result = session.query(DTGuild).filter(DTGuild.id == id).delete()
  session.commit()
  return result > 0

def remove_deleted_guilds(guild_id_list: List[int]) -> int:
  deleted_guilds = session.query(DTGuild).filter(DTGuild.id.not_in(guild_id_list)).delete()
  session.commit()
  return deleted_guilds

def get_guild_level_leaderboard(guild_id: Optional[int]=None) -> List[Tuple[int, int, str, int]]:
  """
  :param guild_id: Optional deep town guild id
  :return: standing, guild id, guild name, guild level
  """

  data = session.execute(f"""
  SELECT position, id, name, level
  FROM (SELECT ROW_NUMBER() OVER(ORDER BY level DESC) AS position, id, name, level
        FROM dt_guilds
        ORDER BY level DESC) as pin
  {f"WHERE id={guild_id}" if guild_id is not None else ""}
  ORDER BY level DESC;
  """).all()

  return data
