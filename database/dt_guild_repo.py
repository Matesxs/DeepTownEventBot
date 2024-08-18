from typing import Optional, List, Tuple
from sqlalchemy import or_, select, delete, text, func

from database import run_commit_in_thread, run_query_in_thread
from database.tables.dt_guild import DTGuild
from database import dt_blacklist_repo
from utils.dt_helpers import DTGuildData

async def get_dt_guild(session, guild_id:int) -> Optional[DTGuild]:
  result = await run_query_in_thread(session, select(DTGuild).filter(DTGuild.id == guild_id))
  return result.scalar_one_or_none()

async def search_guilds(session, search: Optional[str]=None, limit: int=25) -> List[DTGuild]:
  if search is not None:
    if search.isnumeric():
      result = await run_query_in_thread(session, select(DTGuild).filter(or_(DTGuild.name.ilike(f"%{search}%"), DTGuild.id == int(search))).order_by(DTGuild.name).limit(limit))
    else:
      result = await run_query_in_thread(session, select(DTGuild).filter(DTGuild.name.ilike(f"%{search}%")).order_by(DTGuild.name).limit(limit))
  else:
    result = await run_query_in_thread(session, select(DTGuild).order_by(DTGuild.name).limit(limit))
  return result.scalars().all()

async def create_dummy_dt_guild(session, gid: int) -> Optional[DTGuild]:
  item = await get_dt_guild(session, gid)
  if item is None:
    if await dt_blacklist_repo.is_on_blacklist(session, dt_blacklist_repo.BlacklistType.GUILD, gid):
      return None

    item = DTGuild(id=gid, name="Unknown", level=-1)
    session.add(session)
    await run_commit_in_thread(session)

  return item

async def get_and_update_dt_guild(session, guild_data: DTGuildData) -> Optional[DTGuild]:
  item = await get_dt_guild(session, guild_data.id)
  if item is None:
    if await dt_blacklist_repo.is_on_blacklist(session, dt_blacklist_repo.BlacklistType.GUILD, guild_data.id):
      return None

    item = DTGuild(id=guild_data.id, name=guild_data.name, level=guild_data.level, is_active=guild_data.is_active)
    session.add(item)
    await run_commit_in_thread(session)
  else:
    item.update(guild_data)
    await run_commit_in_thread(session)

  return item

async def remove_guild(session, gid: int) -> bool:
  result = await run_query_in_thread(session, delete(DTGuild).filter(DTGuild.id == gid), commit=True)
  return result.rowcount > 0

async def remove_deleted_guilds(session, guild_id_list: List[int]) -> int:
  result = await run_query_in_thread(session, delete(DTGuild).filter(DTGuild.id.not_in(guild_id_list)), commit=True)
  return result.rowcount

async def is_guild_active(session, guild_id: int) -> bool:
  guild = await get_dt_guild(session, guild_id)
  if guild is None: return True
  if guild.is_active: return True
  return False

async def get_inactive_guild_ids(session) -> List[int]:
  result = await run_query_in_thread(session, select(DTGuild.id).filter(DTGuild.is_active == False))
  return result.scalars().all()

async def get_number_of_active_guilds(session) -> int:
  result = await run_query_in_thread(session, select(func.count()).select_from(DTGuild).filter(DTGuild.is_active == True))
  return result.scalar_one()

async def get_number_of_all_guilds(session) -> int:
  result = await run_query_in_thread(session, select(func.count(DTGuild.id)))
  return result.scalar_one()

async def get_guild_level_leaderboard(session) -> List[Tuple[int, int, str, int]]:
  """
  :return: standing, guild id, guild name, guild level
  """

  result = await run_query_in_thread(session, text(f"""
  SELECT position, id, name, level
  FROM (SELECT ROW_NUMBER() OVER(ORDER BY level DESC) AS position, id, name, level
        FROM dt_guilds
        WHERE is_active=TRUE
        ORDER BY level DESC) as pin
  ORDER BY level DESC;
  """))

  return result.all()

async def get_guild_position(session, guild_id: int) -> Optional[int]:
  result = await run_query_in_thread(session, text(f"""
    SELECT position
    FROM (SELECT ROW_NUMBER() OVER(ORDER BY level DESC) AS position, id, name, level
          FROM dt_guilds
          WHERE is_active=TRUE
          ORDER BY level DESC) as pin
    WHERE id={guild_id};
    """))

  return result.scalar_one_or_none()
