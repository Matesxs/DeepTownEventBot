from typing import Optional

from database import session
from database.tables.dt_user import DTUser
from utils.dt_helpers import DTUserData

def get_dt_user(user_id: int) -> Optional[DTUser]:
  return session.query(DTUser).filter(DTUser.id == user_id).one_or_none()

def get_and_update_dt_user(user_data: DTUserData) -> DTUser:
  item = get_dt_user(user_data.id)
  if item is None:
    item = DTUser(id=user_data.id, username=user_data.name, level=user_data.level, depth=user_data.depth, last_online=user_data.last_online)
    session.add(item)
    session.commit()
  else:
    item.username = user_data.name
    item.level = user_data.level
    item.depth = user_data.depth
    item.last_online = user_data.last_online
    session.commit()
  return item
