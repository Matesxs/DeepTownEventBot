from typing import Optional, List

from database import session
from database.tables.dt_user import DTUser
from utils.dt_helpers import DTUserData

def get_dt_user(user_id: int) -> Optional[DTUser]:
  return session.query(DTUser).filter(DTUser.id == user_id).one_or_none()

def get_user_by_username(username: str) -> List[DTUser]:
  return session.query(DTUser).filter(DTUser.username.ilike(username)).all()

def create_dummy_dt_user(id: int) -> DTUser:
  item = get_dt_user(id)
  if item is None:
    item = DTUser(id=id, username="Unknown", level=-1, depth=-1)
    session.add(item)
    session.commit()
  return item

def get_and_update_dt_user(user_data: DTUserData) -> DTUser:
  item = get_dt_user(user_data.id)
  if item is None:
    item = DTUser.from_DTUserData(user_data)
    session.add(item)
  else:
    item.update(user_data)
  session.commit()
  return item
