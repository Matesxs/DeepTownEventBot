import datetime
from typing import Optional, List, Tuple
from sqlalchemy import select

from database import run_query_in_thread
from database.tables.dt_statistics import DTActiveEntitiesData

async def get_day_active_statistics(session, date: datetime.date) -> Optional[DTActiveEntitiesData]:
  result = await run_query_in_thread(session, select(DTActiveEntitiesData).where(DTActiveEntitiesData.date == date))
  return result.scalar_one_or_none()

async def generate_or_update_active_statistics(session) -> DTActiveEntitiesData:
  today = datetime.datetime.now(datetime.UTC).date()
  item = await get_day_active_statistics(session, today)
  if item is None:
    item = await DTActiveEntitiesData.generate(session, today)
  else:
    await item.update(session)
  return item

async def get_active_user_statistics(session, date_threshold: Optional[datetime.date] = None) -> List[Tuple[datetime.datetime, int, int]]:
  if date_threshold is None:
    date_threshold = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=365)).date()

  result = await run_query_in_thread(session, select(DTActiveEntitiesData.date, DTActiveEntitiesData.active_users, DTActiveEntitiesData.all_users)
                                              .where(DTActiveEntitiesData.date >= date_threshold)
                                              .order_by(DTActiveEntitiesData.date))

  return result.all()

async def get_active_guild_statistics(session, date_threshold: Optional[datetime.date] = None) -> List[Tuple[datetime.datetime, int, int]]:
  if date_threshold is None:
    date_threshold = (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=365)).date()

  result = await run_query_in_thread(session, select(DTActiveEntitiesData.date, DTActiveEntitiesData.active_guilds, DTActiveEntitiesData.all_guilds)
                                              .where(DTActiveEntitiesData.date >= date_threshold)
                                              .order_by(DTActiveEntitiesData.date))

  return result.all()
