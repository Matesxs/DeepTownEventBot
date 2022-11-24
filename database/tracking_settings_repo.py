import disnake
from typing import Optional, List

from database import session
from database.tables.tracking_settings import TrackingSettings
from database.guilds_repo import get_or_create_guild_if_not_exist
from database.dt_guild_repo import get_and_update_dt_guild
from utils.dt_helpers import DTGuildData

def get_tracking_settings(guild_id: int, dt_guild_id: int) -> Optional[TrackingSettings]:
  return session.query(TrackingSettings).filter(TrackingSettings.guild_id == str(guild_id), TrackingSettings.dt_guild_id == dt_guild_id).one_or_none()

def get_or_create_tracking_settings(guild: disnake.Guild, dt_guild_data: DTGuildData) -> TrackingSettings:
  item = get_tracking_settings(guild.id, dt_guild_data.id)
  if item is None:
    get_or_create_guild_if_not_exist(guild)
    get_and_update_dt_guild(dt_guild_data)

    item = TrackingSettings(guild_id=str(guild.id), dt_guild_id=dt_guild_data.id)
    session.add(item)
    session.commit()
  return item

def get_all_tracking_settings() -> List[TrackingSettings]:
  return session.query(TrackingSettings).all()

def remove_tracking_settings(guild_id: int, dt_guild_id: int):
  session.query(TrackingSettings).filter(TrackingSettings.guild_id == str(guild_id), TrackingSettings.dt_guild_id == dt_guild_id).delete()
  session.commit()

def get_tracked_guild_ids():
  return session.query(TrackingSettings.dt_guild_id).distinct().all()
