from typing import Optional, List, Tuple
from sqlalchemy import or_, select, delete

from database import run_commit, run_query, session
from database.tables.dt_guild import DTGuild
from database import dt_blacklist_repo, event_participation_guild_repo
from utils.dt_helpers import DTGuildData
from config import config

async def get_dt_guild(guild_id:int) -> Optional[DTGuild]:
  result = await run_query(select(DTGuild).filter(DTGuild.id == guild_id))
  return result.scalar_one_or_none()

async def search_guilds(search: Optional[str]=None, limit: int=25) -> List[DTGuild]:
  if search is not None:
    if search.isnumeric():
      result = await run_query(select(DTGuild).filter(or_(DTGuild.name.ilike(f"%{search}%"), DTGuild.id == int(search))).order_by(DTGuild.name).limit(limit))
    else:
      result = await run_query(select(DTGuild).filter(DTGuild.name.ilike(f"%{search}%")).order_by(DTGuild.name).limit(limit))
  else:
    result = await run_query(select(DTGuild).order_by(DTGuild.name).limit(limit))
  return result.scalars().all()

async def create_dummy_dt_guild(id: int) -> Optional[DTGuild]:
  item = await get_dt_guild(id)
  if item is None:
    if await dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.GUILD, id):
      return None

    item = DTGuild(id=id, name="Unknown", level=-1)
    session.add(item)
    await run_commit()

  return item

async def get_and_update_dt_guild(guild_data: DTGuildData) -> Optional[DTGuild]:
  item = await get_dt_guild(guild_data.id)
  if item is None:
    if await dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.GUILD, guild_data.id):
      return None

    item = DTGuild(id=guild_data.id, name=guild_data.name, level=guild_data.level)
    session.add(item)
  else:
    item.is_active = await event_participation_guild_repo.get_guild_activity(item.id, config.data_manager.guild_activity_check_events, config.data_manager.guild_activity_check_participation_threshold)

    item.name = guild_data.name
    item.level = guild_data.level

  await run_commit()

  return item

async def remove_guild(id: int) -> bool:
  result = await run_query(delete(DTGuild).filter(DTGuild.id == id), commit=True)
  return result.rowcount > 0

async def remove_deleted_guilds(guild_id_list: List[int]) -> int:
  result = await run_query(delete(DTGuild).filter(DTGuild.id.not_in(guild_id_list)), commit=True)
  return result.rowcount

async def is_guild_active(guild_id: int) -> bool:
  guild = await get_dt_guild(guild_id)
  if guild is None: return True
  if guild.is_active: return True
  return False

async def get_inactive_guild_ids() -> List[int]:
  result = await run_query(select(DTGuild.id).filter(DTGuild.is_active == False))
  return result.scalars().all()

async def get_guild_level_leaderboard() -> List[Tuple[int, int, str, int]]:
  """
  :return: standing, guild id, guild name, guild level
  """

  result = await run_query(f"""
  SELECT position, id, name, level
  FROM (SELECT ROW_NUMBER() OVER(ORDER BY level DESC) AS position, id, name, level
        FROM dt_guilds
        WHERE is_active=TRUE
        ORDER BY level DESC) as pin
  ORDER BY level DESC;
  """)

  return result.all()

async def get_guild_position(guild_id: int) -> Optional[int]:
  result = await run_query(f"""
    SELECT position
    FROM (SELECT ROW_NUMBER() OVER(ORDER BY level DESC) AS position, id, name, level
          FROM dt_guilds
          WHERE is_active=TRUE
          ORDER BY level DESC) as pin
    WHERE id={guild_id};
    """)

  return result.scalar_one_or_none()
