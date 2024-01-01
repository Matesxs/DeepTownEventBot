from typing import Optional, List
from sqlalchemy import func, select, delete

from database import run_query, add_item
from database.tables.dt_guild_member import DTGuildMember
from database.dt_guild_repo import get_and_update_dt_guild, create_dummy_dt_guild
from database.dt_user_repo import get_and_update_dt_user, create_dummy_dt_user
from utils.dt_helpers import DTGuildData

async def get_dt_guild_member(user_id: int, guild_id: int) -> Optional[DTGuildMember]:
  result = await run_query(select(DTGuildMember).filter(DTGuildMember.dt_user_id == user_id, DTGuildMember.dt_guild_id == guild_id))
  return result.scalar_one_or_none()

async def create_dummy_dt_guild_member(user_id: int, guild_id: int) -> Optional[DTGuildMember]:
  item = await get_dt_guild_member(user_id, guild_id)
  if item is None:
    if (await create_dummy_dt_guild(guild_id)) is None:
      return None

    if (await create_dummy_dt_user(user_id)) is None:
      return None

    item = DTGuildMember(dt_user_id=user_id, dt_guild_id=guild_id, current_member=False)
    await add_item(item)

  return item

async def get_and_update_dt_guild_members(guild_data: DTGuildData) -> Optional[List[DTGuildMember]]:
  if (await get_and_update_dt_guild(guild_data)) is None:
    return None

  dt_members = []
  current_user_ids = []
  for player_data in guild_data.players:
    if (await get_and_update_dt_user(player_data)) is None:
      continue

    item = await get_dt_guild_member(player_data.id, guild_data.id)
    if item is None:
      item = DTGuildMember(dt_user_id=player_data.id, dt_guild_id=guild_data.id)
      await add_item(item)

    # If this user is marked as current member somewhere else remove it
    # await run_query(delete(DTGuildMember).filter(DTGuildMember.dt_user_id == player_data.id, DTGuildMember.dt_guild_id != guild_data.id), commit=True)

    dt_members.append(item)
    current_user_ids.append(player_data.id)

  # Remove all users that are not in current guild data and are marked currently as current member
  await run_query(delete(DTGuildMember).filter(DTGuildMember.dt_guild_id == guild_data.id, DTGuildMember.dt_user_id.notin_(current_user_ids)), commit=True)

  return dt_members

async def get_number_of_members(guild_id: int) -> int:
  result = await run_query(select(func.count(DTGuildMember.dt_user_id)).filter(DTGuildMember.dt_guild_id == guild_id))
  return result.scalar_one_or_none()
