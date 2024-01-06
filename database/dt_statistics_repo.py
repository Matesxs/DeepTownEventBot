import datetime
from typing import Optional, List, Tuple
from sqlalchemy import select

from database import run_query
from database.tables.dt_statistics import DTActiveEntitiesData

async def get_active_user_statistics(date_threshold: Optional[datetime.datetime] = None) -> List[Tuple[datetime.datetime, int, int]]:
  if date_threshold is None:
    date_threshold = datetime.datetime.utcnow() - datetime.timedelta(days=365)

  result = await run_query(select(DTActiveEntitiesData.date, DTActiveEntitiesData.active_users, DTActiveEntitiesData.all_users)
                           .where(DTActiveEntitiesData.date >= date_threshold)
                           .order_by(DTActiveEntitiesData.date))

  return result.all()

async def get_active_guild_statistics(date_threshold: Optional[datetime.datetime] = None) -> List[Tuple[datetime.datetime, int, int]]:
  if date_threshold is None:
    date_threshold = datetime.datetime.utcnow() - datetime.timedelta(days=365)

  result = await run_query(select(DTActiveEntitiesData.date, DTActiveEntitiesData.active_guilds, DTActiveEntitiesData.all_guilds)
                           .where(DTActiveEntitiesData.date >= date_threshold)
                           .order_by(DTActiveEntitiesData.date))

  return result.all()
