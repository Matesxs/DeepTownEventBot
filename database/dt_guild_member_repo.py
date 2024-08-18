from typing import Optional, List
from sqlalchemy import func, select, delete

from database import run_query_in_thread, run_commit_in_thread
from database.tables.dt_guild_member import DTGuildMember
from database.dt_guild_repo import get_and_update_dt_guild, create_dummy_dt_guild
from database.dt_user_repo import get_and_update_dt_user, create_dummy_dt_user
from database.dt_member_criteria import have_participation_elsewhere
from utils.dt_helpers import DTGuildData
from utils.logger import setup_custom_logger

logger = setup_custom_logger(__name__)

async def get_dt_guild_member(session, user_id: int, guild_id: int) -> Optional[DTGuildMember]:
  result = await run_query_in_thread(session, select(DTGuildMember).filter(DTGuildMember.dt_user_id == user_id, DTGuildMember.dt_guild_id == guild_id))
  return result.scalar_one_or_none()

async def create_dummy_dt_guild_member(session, user_id: int, guild_id: int, event_year: Optional[int] = None, event_week: Optional[int] = None, contribution_amount: Optional[int] = None) -> Optional[DTGuildMember]:
  item = await get_dt_guild_member(session, user_id, guild_id)
  if item is None:
    if event_year is not None and event_week is not None and contribution_amount is not None:
      # If this player have this specific event already participation in other guild, dont create him
      if not await have_participation_elsewhere(session, user_id, guild_id, event_year, event_week, contribution_amount):
        # logger.info(f"Skipped creation of dummy member for user {user_id} in guild {guild_id} because of participation elsewhere")
        return None

    if (await create_dummy_dt_guild(session, guild_id)) is None:
      return None

    if (await create_dummy_dt_user(session, user_id)) is None:
      return None

    # Remove all other memberships asociated with this used id
    await run_query_in_thread(session, delete(DTGuildMember).filter(DTGuildMember.dt_guild_id != guild_id, DTGuildMember.dt_user_id == user_id), commit=True)

    item = DTGuildMember(dt_user_id=user_id, dt_guild_id=guild_id)
    session.add(item)
    await run_commit_in_thread(session)

  return item

async def get_and_update_dt_guild_members(session, guild_data: DTGuildData, event_year: Optional[int] = None, event_week: Optional[int] = None) -> Optional[List[DTGuildMember]]:
  if (await get_and_update_dt_guild(session, guild_data)) is None:
    return None

  dt_members = []
  current_user_ids = []
  for player_data in guild_data.players:
    if (await get_and_update_dt_user(session, player_data)) is None:
      continue

    item = await get_dt_guild_member(session, player_data.id, guild_data.id)
    if item is None:
      if event_year is not None and event_week is not None:
        # If this player have this specific event already participation in other guild, dont create him
        if not await have_participation_elsewhere(session, player_data.id, guild_data.id, event_year, event_week, player_data.last_event_contribution):
          # logger.info(f"Skipped creation of member for user {player_data.id} in guild {guild_data.id} because of participation elsewhere")
          continue

      item = DTGuildMember(dt_user_id=player_data.id, dt_guild_id=guild_data.id)
      session.add(item)
      await run_commit_in_thread(session)

    dt_members.append(item)
    current_user_ids.append(player_data.id)

  # Remove all users that are not in current guild data and are marked currently as current member
  await run_query_in_thread(session, delete(DTGuildMember).filter(DTGuildMember.dt_guild_id == guild_data.id, DTGuildMember.dt_user_id.notin_(current_user_ids)), commit=True)

  return dt_members

async def get_number_of_members(session, guild_id: int) -> int:
  result = await run_query_in_thread(session, select(func.count(DTGuildMember.dt_user_id)).filter(DTGuildMember.dt_guild_id == guild_id))
  return result.scalar_one_or_none()
