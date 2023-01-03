from typing import Optional, List

from database import session
from database.tables.dt_user import DTUser
from utils.dt_helpers import DTUserData
from database import dt_blacklist_repo

all_users_cache = None

def get_dt_user(user_id: int) -> Optional[DTUser]:
  return session.query(DTUser).filter(DTUser.id == user_id).one_or_none()

def get_all_users() -> List[DTUser]:
  global all_users_cache

  if all_users_cache is None:
    all_users_cache = session.query(DTUser).all()

  return all_users_cache

def get_users_by_identifier(identifier: str) -> List[DTUser]:
  if identifier.isnumeric():
    result = get_dt_user(int(identifier))
    if result is not None:
      return [result]

  return session.query(DTUser).filter(DTUser.username.ilike(identifier)).all()

def create_dummy_dt_user(id: int) -> Optional[DTUser]:
  global all_users_cache

  item = get_dt_user(id)
  if item is None:
    if dt_blacklist_repo.get_blacklist_item(dt_blacklist_repo.BlacklistType.USER, id) is not None:
      return None

    item = DTUser(id=id, username="Unknown", level=-1, depth=-1)
    session.add(item)
    session.commit()

    all_users_cache = None
  return item

def remove_user(id: int) -> bool:
  result = session.query(DTUser).filter(DTUser.id == id).delete()
  session.commit()
  return result > 0

def get_and_update_dt_user(user_data: DTUserData) -> Optional[DTUser]:
  global all_users_cache

  item = get_dt_user(user_data.id)
  if item is None:
    if dt_blacklist_repo.get_blacklist_item(dt_blacklist_repo.BlacklistType.USER, user_data.id) is not None:
      return None

    item = DTUser.from_DTUserData(user_data)
    session.add(item)

    all_users_cache = None
  else:
    item.update(user_data)
  session.commit()
  return item
