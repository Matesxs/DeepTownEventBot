from typing import Optional, List
from sqlalchemy import or_, select, delete, func
import datetime

from config import config
from database import run_commit_in_thread, run_query_in_thread
from database.tables.dt_user import DTUser
from utils.dt_helpers import DTUserData
from database import dt_blacklist_repo

async def get_dt_user(session, user_id: int) -> Optional[DTUser]:
  result = await run_query_in_thread(session, select(DTUser).filter(DTUser.id == user_id))
  return result.scalar_one_or_none()

async def get_all_users(session, search: Optional[str]=None, limit: int=25) -> List[DTUser]:
  if search is not None:
    if search.isnumeric():
      result = await run_query_in_thread(session, select(DTUser).filter(or_(DTUser.username.ilike(f"%{search}%"), DTUser.id == int(search))).order_by(DTUser.username).limit(limit))
    else:
      result = await run_query_in_thread(session, select(DTUser).filter(DTUser.username.ilike(f"%{search}%")).order_by(DTUser.username).limit(limit))
  else:
    result = await run_query_in_thread(session, select(DTUser).order_by(DTUser.username).limit(limit))
  return result.scalars().all()

async def create_dummy_dt_user(session, user_id: int) -> Optional[DTUser]:
  item = await get_dt_user(session, user_id)
  if item is None:
    if await dt_blacklist_repo.is_on_blacklist(session, dt_blacklist_repo.BlacklistType.USER, user_id):
      return None

    item = DTUser(id=user_id, username="Unknown", level=-1, depth=-1)
    session.add(item)
    await run_commit_in_thread(session)
  return item

async def remove_user(session, user_id: int) -> bool:
  result = await run_query_in_thread(session, delete(DTUser).filter(DTUser.id == user_id), commit=True)
  return result.rowcount > 0

async def get_and_update_dt_user(session, user_data: DTUserData) -> Optional[DTUser]:
  item = await get_dt_user(session, user_data.id)
  if item is None:
    if await dt_blacklist_repo.is_on_blacklist(session, dt_blacklist_repo.BlacklistType.USER, user_data.id):
      return None

    item = DTUser.from_DTUserData(user_data)
    session.add(item)
    await run_commit_in_thread(session)
  else:
    item.update(user_data)
    await run_commit_in_thread(session)

  return item

async def get_number_of_active_users(session) -> int:
  result = await run_query_in_thread(session, select(func.count(DTUser.id)).filter((DTUser.last_online + datetime.timedelta(days=config.data_manager.activity_days_threshold)) > datetime.datetime.utcnow()))
  return result.scalar_one()

async def get_number_of_all_users(session) -> int:
  result = await run_query_in_thread(session, select(func.count(DTUser.id)))
  return result.scalar_one()
