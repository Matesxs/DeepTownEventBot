from typing import Optional, List
from sqlalchemy import or_

from database import session
from database.tables.dt_user import DTUser
from utils.dt_helpers import DTUserData
from database import dt_blacklist_repo

def get_dt_user(user_id: int) -> Optional[DTUser]:
  return session.query(DTUser).filter(DTUser.id == user_id).one_or_none()

def get_all_users(search: Optional[str]=None, limit: int=25) -> List[DTUser]:
  if search is not None:
    if search.isnumeric():
      return session.query(DTUser).filter(or_(DTUser.username.ilike(f"%{search}%"), DTUser.id == int(search))).limit(limit).all()
    else:
      return session.query(DTUser).filter(DTUser.username.ilike(f"%{search}%")).limit(limit).all()
  return session.query(DTUser).limit(limit).all()

def get_users_by_identifier(identifier: str) -> List[DTUser]:
  if identifier.isnumeric():
    result = get_dt_user(int(identifier))
    if result is not None:
      return [result]

  return session.query(DTUser).filter(DTUser.username.ilike(identifier)).all()

def create_dummy_dt_user(id: int) -> Optional[DTUser]:
  item = get_dt_user(id)
  if item is None:
    if dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.USER, id):
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
    if dt_blacklist_repo.is_on_blacklist(dt_blacklist_repo.BlacklistType.USER, user_data.id):
      return None

    item = DTUser.from_DTUserData(user_data)
    session.add(item)
  else:
    item.update(user_data)
  session.commit()
  return item
