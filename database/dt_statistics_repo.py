import datetime
from typing import Optional, List, Tuple
from sqlalchemy import select

from database import run_query
from database.tables.dt_statistics import DTActiveEntitiesData

async def get_day_active_statistics(date: datetime.date) -> Optional[DTActiveEntitiesData]:
  result = await run_query(select(DTActiveEntitiesData).where(DTActiveEntitiesData.date == date))
  return result.scalar_one_or_none()

async def generate_or_update_active_statistics() -> DTActiveEntitiesData:
  today = datetime.datetime.utcnow().date()
  item = await get_day_active_statistics(today)
  if item is None:
    item = await DTActiveEntitiesData.generate(today)
  else:
    await item.update()
  return item

async def get_active_user_statistics(date_threshold: Optional[datetime.date] = None) -> List[Tuple[datetime.datetime, int, int]]:
  if date_threshold is None:
    date_threshold = (datetime.datetime.utcnow() - datetime.timedelta(days=365)).date()

  result = await run_query(select(DTActiveEntitiesData.date, DTActiveEntitiesData.active_users, DTActiveEntitiesData.all_users)
                           .where(DTActiveEntitiesData.date >= date_threshold)
                           .order_by(DTActiveEntitiesData.date))

  return result.all()

async def get_active_guild_statistics(date_threshold: Optional[datetime.date] = None) -> List[Tuple[datetime.datetime, int, int]]:
  if date_threshold is None:
    date_threshold = (datetime.datetime.utcnow() - datetime.timedelta(days=365)).date()

  result = await run_query(select(DTActiveEntitiesData.date, DTActiveEntitiesData.active_guilds, DTActiveEntitiesData.all_guilds)
                           .where(DTActiveEntitiesData.date >= date_threshold)
                           .order_by(DTActiveEntitiesData.date))

  return result.all()
