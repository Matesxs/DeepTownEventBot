from typing import Optional, List, Tuple
from sqlalchemy import select, delete, func, literal_column

from database import run_query, run_commit, session, event_participation_repo
from database.tables.dt_items import EventItem, DTItem, ItemType, ItemSource, DTItemComponentMapping

async def get_dt_item(name: str) -> Optional[DTItem]:
  result = await run_query(select(DTItem).filter(DTItem.name == name))
  return result.scalar_one_or_none()

async def set_dt_item(name: str, item_type: ItemType, item_source: ItemSource, value: Optional[float], crafting_time: Optional[float], crafting_batch_size: Optional[int]) -> DTItem:
  item = await get_dt_item(name)
  if item is None:
    item = DTItem(name=name)
    session.add(item)

  item.item_type = item_type
  item.item_source = item_source
  item.value = value if value is not None else 0
  item.crafting_time = crafting_time if (crafting_time is not None and item_type == ItemType.CRAFTABLE) else 0
  item.crafting_batch_size = crafting_batch_size if (crafting_batch_size is not None and item_type == ItemType.CRAFTABLE) else 1

  await run_commit()
  return item

async def remove_dt_item(name: str) -> bool:
  result = await run_query(delete(DTItem).filter(DTItem.name == name))
  await run_commit()
  return result.rowcount > 0

async def search_items(search: Optional[str]=None, limit: int=20) -> List[str]:
  if search is None:
    query = select(DTItem.name).order_by(DTItem.name)
  else:
    query = select(DTItem.name).filter(DTItem.name.ilike(f"%{search}%")).order_by(DTItem.name)
  result = await run_query(query.limit(limit))
  return result.scalars().all()

async def search_craftable_items(search: Optional[str]=None, limit: int=20) -> List[DTItem]:
  if search is None:
    query = select(DTItem.name).filter(DTItem.item_type == ItemType.CRAFTABLE).order_by(DTItem.name)
  else:
    query = select(DTItem.name).filter(DTItem.item_type == ItemType.CRAFTABLE, DTItem.name.ilike(f"%{search}%")).order_by(DTItem.name)
  result = await run_query(query.limit(limit))
  return result.scalars().all()

async def get_all_dt_items() -> List[DTItem]:
  result = await run_query(select(DTItem).order_by(DTItem.name))
  return result.scalars().all()

async def get_component_mapping(target_item_name: str, component_item_name: str) -> Optional[DTItemComponentMapping]:
  result = await run_query(select(DTItemComponentMapping).filter(DTItemComponentMapping.target_item_name == target_item_name, DTItemComponentMapping.component_item_name == component_item_name))
  return result.scalars().all()

async def set_component_mapping(target_item_name: str, component_item_name: str, amount: float=1.0) -> Optional[DTItemComponentMapping]:
  item = await get_component_mapping(target_item_name, component_item_name)
  if item is None:
    target_item = await get_dt_item(target_item_name)
    component_item = await get_dt_item(component_item_name)

    if target_item is None or component_item is None or target_item.item_type != ItemType.CRAFTABLE:
      return None

    item = DTItemComponentMapping(target_item_name=target_item_name, component_item_name=component_item_name)
    session.add(item)

  item.amount = amount

  await run_commit()
  return item

async def remove_component_mapping(target_item_name: str, component_item_name: str) -> bool:
  result = await run_query(delete(DTItemComponentMapping).filter(DTItemComponentMapping.target_item_name == target_item_name, DTItemComponentMapping.component_item_name == component_item_name))
  await run_commit()
  return result.rowcount > 0

async def remove_all_component_mappings(target_item_name: str) -> bool:
  result = await run_query(delete(DTItemComponentMapping).filter(DTItemComponentMapping.target_item_name == target_item_name))
  await run_commit()
  return result.rowcount > 0

async def get_event_item(name: str, event_id: int) -> Optional[EventItem]:
  result = await run_query(select(EventItem).filter(EventItem.item_name == name, EventItem.event_id == event_id))
  return result.scalar_one_or_none()

async def set_event_item(event_year: int, event_week: int, item_name: str, base_amount: Optional[int], commit: bool=True) -> Optional[EventItem]:
  if (await get_dt_item(item_name)) is None:
    return None

  event_specification = await event_participation_repo.get_or_create_event_specification(event_year, event_week)

  item = await get_event_item(item_name, event_specification.event_id)
  if item is None:
    item = EventItem(event_id=event_specification.event_id, item_name=item_name)
    session.add(item)

  item.base_amount = base_amount

  if commit:
    await run_commit()
  return item

async def remove_event_participation_items(event_year: int, event_week: int) -> bool:
  event_spec = await event_participation_repo.get_event_specification(event_year, event_week)
  if event_spec is None: return False

  result = await run_query(delete(EventItem).filter(EventItem.event_id == event_spec.event_id))
  await run_commit()
  return result.rowcount > 0

async def get_event_items_history(limit: int=500) -> List[Tuple[int, int, Optional[str]]]:
  result = await run_query(select(event_participation_repo.EventSpecification.event_year, event_participation_repo.EventSpecification.event_week, func.string_agg(EventItem.item_name, literal_column("',\n'")))
                           .join(EventItem, isouter=True)
                           .group_by(event_participation_repo.EventSpecification.event_year, event_participation_repo.EventSpecification.event_week)
                           .order_by(event_participation_repo.EventSpecification.event_year.desc(), event_participation_repo.EventSpecification.event_week.desc())
                           .limit(limit))
  return result.all()
