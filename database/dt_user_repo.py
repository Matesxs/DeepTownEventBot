from typing import Optional, List
from sqlalchemy import or_, select, delete

from database import run_commit, run_query, add_item
from database.tables.dt_user import DTUser
from utils.dt_helpers import DTUserData
from database import dt_blacklist_repo
async def get_dt_user(user_id: int) -> Optional[DTUser]:
  result = await run_query(select(DTUser).filter(DTUser.id == user_id))
  return result.scalar_one_or_none()

async def get_all_users(search: Optional[str]=None, limit: int=25) -> List[DTUser]:
  if search is not None:
    if search.isnumeric():
      result = await run_query(select(DTUser).filter(or_(DTUser.username.ilike(f"%{search}%"), DTUser.id == int(search))).order_by(DTUser.username).limit(limit))
    else:
      result = await run_query(select(DTUser).filter(DTUser.username.ilike(f"%{search}%")).order_by(DTUser.username).limit(limit))
  else:
    result = await run_query(select(DTUser).order_by(DTUser.username).limit(limit))
  return result.scalars().all()

async def create_dummy_dt_user(id: int) -> Optional[DTUser]:
  item = await get_dt_user(id)
  if item is None:
    if await dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.USER, id):
      return None

    item = DTUser(id=id, username="Unknown", level=-1, depth=-1)
    await add_item(item)
  return item

async def remove_user(id: int) -> bool:
  result = await run_query(delete(DTUser).filter(DTUser.id == id), commit=True)
  return result.rowcount > 0

async def get_and_update_dt_user(user_data: DTUserData) -> Optional[DTUser]:
  item = await get_dt_user(user_data.id)
  if item is None:
    if await dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.USER, user_data.id):
      return None

    item = DTUser.from_DTUserData(user_data)
    await add_item(item)
  else:
    item.update(user_data)
    await run_commit()

  return item
