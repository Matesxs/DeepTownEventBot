from typing import Optional, List

from database import session, event_participation_repo
from database.tables.dt_items import EventItem, DTItem

def get_dt_item(name: str) -> Optional[DTItem]:
  return session.query(DTItem).filter(DTItem.name == name).one_or_none()

def set_dt_item(name: str, value: Optional[float]) -> DTItem:
  item = get_dt_item(name)
  if item is None:
    item = DTItem(name=name)
    session.add(item)
  item.value = value if value is not None else 0
  session.commit()
  return item

def remove_dt_item(name: str) -> bool:
  deleted = session.query(DTItem).filter(DTItem.name == name).delete()
  session.commit()
  return deleted > 0

def get_all_dt_item_names() -> List[str]:
  data = session.query(DTItem.name).order_by(DTItem.name).all()
  return [d[0] for d in data]

def get_all_dt_items() -> List[DTItem]:
  return session.query(DTItem).all()

def get_event_item(name: str, event_id: int) -> Optional[EventItem]:
  return session.query(EventItem).filter(EventItem.item_name == name, EventItem.event_id == event_id).one_or_none()

def set_event_item(event_year: int, event_week: int, item_name: str, base_amount: Optional[int], commit: bool=True) -> Optional[EventItem]:
  if get_dt_item(item_name) is None:
    return None

  event_specification = event_participation_repo.get_or_create_event_specification(event_year, event_week)

  item = get_event_item(item_name, event_specification.event_id)
  if item is None:
    item = EventItem(event_id=event_specification.event_id, item_name=item_name)
    session.add(item)
  item.base_amount = base_amount if base_amount is not None else 0

  if commit:
    session.commit()
  return item

def remove_event_participation_items(event_year: int, event_week: int) -> bool:
  event_spec = event_participation_repo.get_event_specification(event_year, event_week)
  if event_spec is None: return False

  deleted = session.query(EventItem).filter(EventItem.event_id == event_spec.event_id).delete()
  session.commit()
  return deleted > 0