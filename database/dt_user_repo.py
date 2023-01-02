from typing import Optional, List

from database import session
from database.tables.dt_user import DTUser
from utils.dt_helpers import DTUserData
from database import dt_blacklist_repo

def get_dt_user(user_id: int) -> Optional[DTUser]:
  return session.query(DTUser).filter(DTUser.id == user_id).one_or_none()

def get_users_by_username(username: str) -> List[DTUser]:
  return session.query(DTUser).filter(DTUser.username.ilike(username)).all()

def create_dummy_dt_user(id: int) -> Optional[DTUser]:
  item = get_dt_user(id)
  if item is None:
    if dt_blacklist_repo.get_blacklist_item(dt_blacklist_repo.BlacklistType.USER, id) is not None:
      return None

    item = DTUser(id=id, username="Unknown", level=-1, depth=-1)
    session.add(item)
    session.commit()
  return item

def remove_user(id: int) -> bool:
  result = session.query(DTUser).filter(DTUser.id == id).delete()
  session.commit()
  return result > 0

def get_and_update_dt_user(user_data: DTUserData) -> Optional[DTUser]:
  item = get_dt_user(user_data.id)
  if item is None:
    if dt_blacklist_repo.get_blacklist_item(dt_blacklist_repo.BlacklistType.USER, user_data.id) is not None:
      return None

    item = DTUser.from_DTUserData(user_data)
    session.add(item)
  else:
    item.update(user_data)
  session.commit()
  return item
