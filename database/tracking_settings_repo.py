import disnake
from typing import Optional, List, AsyncIterator
from sqlalchemy import select, delete

from database import run_query, run_commit, session
from database.tables.tracking_settings import TrackingSettings
from database.guilds_repo import get_or_create_discord_guild
from database.dt_guild_repo import get_dt_guild

async def get_tracking_settings(guild_id: int, dt_guild_id: int) -> Optional[TrackingSettings]:
  result = await run_query(select(TrackingSettings).filter(TrackingSettings.guild_id == str(guild_id), TrackingSettings.dt_guild_id == dt_guild_id))
  return result.scalar_one_or_none()

async def get_or_create_tracking_settings(guild: disnake.Guild, dt_guild_id: int, announce_channel_id:Optional[int]=None) -> Optional[TrackingSettings]:
  item = await get_tracking_settings(guild.id, dt_guild_id)
  if item is None:
    await get_or_create_discord_guild(guild)
    if (await get_dt_guild(dt_guild_id)) is None:
      return None

    item = TrackingSettings(guild_id=str(guild.id), dt_guild_id=dt_guild_id, announce_channel_id=str(announce_channel_id) if announce_channel_id is not None else None)
    session.add(item)
  else:
    item.announce_channel_id=str(announce_channel_id) if announce_channel_id is not None else None

  await run_commit()
  return item

async def remove_tracking_settings(guild_id: int, dt_guild_id: int) -> bool:
  result = await run_query(delete(TrackingSettings).filter(TrackingSettings.guild_id == str(guild_id), TrackingSettings.dt_guild_id == dt_guild_id))
  await run_commit()
  return result.rowcount > 0

async def get_tracked_guild_ids() -> List[int]:
  result = await run_query(select(TrackingSettings.dt_guild_id).distinct())
  return result.scalars().all()

async def get_all_guild_trackers(guild_id: int) -> List[TrackingSettings]:
  result = await run_query(select(TrackingSettings).filter(TrackingSettings.guild_id == str(guild_id)))
  return result.scalars().all()

async def get_all_trackers() -> AsyncIterator[TrackingSettings]:
  result = await run_query(select(TrackingSettings).execution_options(yield_per=10))
  for partition in result.partitions():
    for row in partition:
      yield row[0]
