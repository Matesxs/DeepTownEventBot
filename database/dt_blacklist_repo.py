from typing import Optional, List, Union

from database import session
from database.tables.dt_blacklist import BlacklistType, DTBlacklistItem

def get_blacklist_item(bl_type: BlacklistType, identifier: int) -> Optional[DTBlacklistItem]:
  return session.query(DTBlacklistItem).filter(DTBlacklistItem.bl_type == BlacklistType(bl_type), DTBlacklistItem.identifier == identifier).one_or_none()

def get_blacklist_items(bl_type: Optional[BlacklistType]=None) -> List[DTBlacklistItem]:
  if bl_type is not None:
    return session.query(DTBlacklistItem).filter(DTBlacklistItem.bl_type == BlacklistType(bl_type)).all()
  return session.query(DTBlacklistItem).all()

def search_blacklist_item(bl_type: BlacklistType, search_term: Union[str, int]) -> List[DTBlacklistItem]:
  if isinstance(search_term, int) or search_term.isnumeric():
    search_term = int(search_term)

    item = get_blacklist_item(bl_type, search_term)
    if item is not None:
      return [item]

  return session.query(DTBlacklistItem).filter(DTBlacklistItem.bl_type == BlacklistType(bl_type), DTBlacklistItem.additional_data.ilike(str(search_term))).all()

def create_blacklist_item(bl_type: BlacklistType, identifier: int, additional_data: Optional[str]=None) -> Optional[DTBlacklistItem]:
  item = get_blacklist_item(bl_type, identifier)
  if item is not None: return None

  item = DTBlacklistItem(bl_type=BlacklistType(bl_type), identifier=identifier, additional_data=additional_data)
  session.add(item)
  session.commit()
  return item

def remove_blacklist_item(bl_type: BlacklistType, identifier: int) -> bool:
  result = session.query(DTBlacklistItem).filter(DTBlacklistItem.bl_type == BlacklistType(bl_type), DTBlacklistItem.identifier == identifier).delete()
  session.commit()
  return result > 0
