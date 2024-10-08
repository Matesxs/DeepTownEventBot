import disnake
from typing import Optional, List, AsyncIterator
from sqlalchemy import select, delete, or_

from database import run_query_in_thread, run_commit_in_thread, dt_guild_repo
from database.tables.tracking_settings import TrackingSettings
from database.discord_objects_repo import get_or_create_discord_guild

async def get_tracking_settings(session, guild_id: int, dt_guild_id: int) -> Optional[TrackingSettings]:
  result = await run_query_in_thread(session, select(TrackingSettings).filter(TrackingSettings.guild_id == str(guild_id), TrackingSettings.dt_guild_id == dt_guild_id))
  return result.scalar_one_or_none()

async def search_tracked_guilds(session, guild_id: int, search: Optional[str]=None, limit: int=25) -> List[dt_guild_repo.DTGuild]:
  if search is not None:
    if search.isnumeric():
      result = await run_query_in_thread(session, select(dt_guild_repo.DTGuild).join(TrackingSettings).filter(or_(dt_guild_repo.DTGuild.name.ilike(f"%{search}%"), dt_guild_repo.DTGuild.id == int(search)), TrackingSettings.guild_id == str(guild_id)).order_by(dt_guild_repo.DTGuild.name).limit(limit))
    else:
      result = await run_query_in_thread(session, select(dt_guild_repo.DTGuild).join(TrackingSettings).filter(dt_guild_repo.DTGuild.name.ilike(f"%{search}%"), TrackingSettings.guild_id == str(guild_id)).order_by(dt_guild_repo.DTGuild.name).limit(limit))
  else:
    result = await run_query_in_thread(session, select(dt_guild_repo.DTGuild).join(TrackingSettings).filter(TrackingSettings.guild_id == str(guild_id)).order_by(dt_guild_repo.DTGuild.name).limit(limit))
  return result.scalars().all()

async def get_or_create_tracking_settings(session, guild: disnake.Guild, dt_guild_id: int, text_announce_channel_id:Optional[int]=None, csv_announce_channel_id:Optional[int]=None) -> Optional[TrackingSettings]:
  item = await get_tracking_settings(session, guild.id, dt_guild_id)
  if item is None:
    await get_or_create_discord_guild(session, guild)
    if (await dt_guild_repo.get_dt_guild(session, dt_guild_id)) is None:
      return None

    item = TrackingSettings(guild_id=str(guild.id), dt_guild_id=dt_guild_id, text_announce_channel_id=str(text_announce_channel_id) if text_announce_channel_id is not None else None, csv_announce_channel_id=str(csv_announce_channel_id) if csv_announce_channel_id is not None else None)
    session.add(item)
    await run_commit_in_thread(session)
  else:
    item.text_announce_channel_id=str(text_announce_channel_id) if text_announce_channel_id is not None else None
    item.csv_announce_channel_id=str(csv_announce_channel_id) if csv_announce_channel_id is not None else None
    await run_commit_in_thread(session)
  return item

async def remove_tracking_settings(session, guild_id: int, dt_guild_id: int) -> bool:
  result = await run_query_in_thread(session, delete(TrackingSettings).filter(TrackingSettings.guild_id == str(guild_id), TrackingSettings.dt_guild_id == dt_guild_id), commit=True)
  return result.rowcount > 0

async def get_tracked_guild_ids(session) -> List[int]:
  result = await run_query_in_thread(session, select(TrackingSettings.dt_guild_id).distinct())
  return result.scalars().all()

async def get_all_guild_trackers(session, guild_id: int) -> List[TrackingSettings]:
  result = await run_query_in_thread(session, select(TrackingSettings).filter(TrackingSettings.guild_id == str(guild_id)))
  return result.scalars().all()

async def get_all_trackers(session) -> AsyncIterator[TrackingSettings]:
  result = await run_query_in_thread(session, select(TrackingSettings).execution_options(yield_per=50))
  for partition in result.partitions():
    for row in partition:
      yield row[0]
