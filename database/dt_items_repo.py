from typing import Optional, List, Tuple
from sqlalchemy import select, delete, func, literal_column

from database import run_query_in_thread, run_commit_in_thread, event_participation_repo
from database.tables.dt_items import EventItem, DTItem, ItemType, ItemSource, DTItemComponentMapping

async def get_dt_item(session, name: str) -> Optional[DTItem]:
  result = await run_query_in_thread(session, select(DTItem).filter(DTItem.name == name))
  return result.scalar_one_or_none()

async def set_dt_item(session, name: str, item_type: ItemType, item_source: ItemSource, value: Optional[float], crafting_time: Optional[float], crafting_batch_size: Optional[int]) -> DTItem:
  item = await get_dt_item(session, name)
  if item is None:
    item = DTItem(name=name)
    session.add(item)
    await run_commit_in_thread(session)

  item.item_type = item_type
  item.item_source = item_source
  item.value = value if value is not None else 0
  item.crafting_time = crafting_time if (crafting_time is not None and item_type == ItemType.CRAFTABLE) else 0
  item.crafting_batch_size = crafting_batch_size if (crafting_batch_size is not None and item_type == ItemType.CRAFTABLE) else 1

  await run_commit_in_thread(session)
  return item

async def remove_dt_item(session, name: str) -> bool:
  result = await run_query_in_thread(session, delete(DTItem).filter(DTItem.name == name), commit=True)
  return result.rowcount > 0

async def search_items(session, search: Optional[str]=None, limit: int=20) -> List[str]:
  if search is None:
    query = select(DTItem.name).order_by(DTItem.name)
  else:
    query = select(DTItem.name).filter(DTItem.name.ilike(f"%{search}%")).order_by(DTItem.name)
  result = await run_query_in_thread(session, query.limit(limit))
  return result.scalars().all()

async def search_craftable_items(session, search: Optional[str]=None, limit: int=20) -> List[DTItem]:
  if search is None:
    query = select(DTItem.name).filter(DTItem.item_type == ItemType.CRAFTABLE).order_by(DTItem.name)
  else:
    query = select(DTItem.name).filter(DTItem.item_type == ItemType.CRAFTABLE, DTItem.name.ilike(f"%{search}%")).order_by(DTItem.name)
  result = await run_query_in_thread(session, query.limit(limit))
  return result.scalars().all()

async def get_all_dt_items(session) -> List[DTItem]:
  result = await run_query_in_thread(session, select(DTItem).order_by(DTItem.name))
  return result.scalars().all()

async def get_all_item_names(session) -> List[str]:
  result = await run_query_in_thread(session, select(DTItem.name))
  return result.scalars().all()

async def get_component_mapping(session, target_item_name: str, component_item_name: str) -> Optional[DTItemComponentMapping]:
  result = await run_query_in_thread(session, select(DTItemComponentMapping).filter(DTItemComponentMapping.target_item_name == target_item_name, DTItemComponentMapping.component_item_name == component_item_name))
  return result.scalars().all()

async def set_component_mapping(session, target_item_name: str, component_item_name: str, amount: float=1.0) -> Optional[DTItemComponentMapping]:
  item = await get_component_mapping(session, target_item_name, component_item_name)
  if item is None:
    target_item = await get_dt_item(session, target_item_name)
    component_item = await get_dt_item(session, component_item_name)

    if target_item is None or component_item is None or target_item.item_type != ItemType.CRAFTABLE:
      return None

    item = DTItemComponentMapping(target_item_name=target_item_name, component_item_name=component_item_name, amount=amount)
    session.add(item)
    await run_commit_in_thread(session)
  else:
    item.amount = amount
    await run_commit_in_thread(session)

  return item

async def remove_component_mapping(session, target_item_name: str, component_item_name: str) -> bool:
  result = await run_query_in_thread(session, delete(DTItemComponentMapping).filter(DTItemComponentMapping.target_item_name == target_item_name, DTItemComponentMapping.component_item_name == component_item_name), commit=True)
  return result.rowcount > 0

async def remove_all_component_mappings(session, target_item_name: str) -> bool:
  result = await run_query_in_thread(session, delete(DTItemComponentMapping).filter(DTItemComponentMapping.target_item_name == target_item_name), commit=True)
  return result.rowcount > 0

async def get_event_item(session, name: str, event_id: int) -> Optional[EventItem]:
  result = await run_query_in_thread(session, select(EventItem).filter(EventItem.item_name == name, EventItem.event_id == event_id))
  return result.scalar_one_or_none()

async def set_event_item(session, event_year: int, event_week: int, item_name: str, base_amount: Optional[int], commit: bool=True) -> Optional[EventItem]:
  if (await get_dt_item(session, item_name)) is None:
    return None

  event_specification = await event_participation_repo.get_or_create_event_specification(session, event_year, event_week)

  item = await get_event_item(session, item_name, event_specification.event_id)
  if item is None:
    item = EventItem(event_id=event_specification.event_id, item_name=item_name)
    session.add(item)

  item.base_amount = base_amount

  if commit:
    await run_commit_in_thread(session)
  return item

async def remove_event_participation_items(session, event_year: int, event_week: int) -> bool:
  event_spec = await event_participation_repo.get_event_specification(session, event_year, event_week)
  if event_spec is None: return False

  result = await run_query_in_thread(session, delete(EventItem).filter(EventItem.event_id == event_spec.event_id), commit=True)
  return result.rowcount > 0

async def get_event_items_history(session, limit: int=500) -> List[Tuple[int, int, Optional[str]]]:
  result = await run_query_in_thread(session, select(event_participation_repo.EventSpecification.event_year, event_participation_repo.EventSpecification.event_week, func.string_agg(EventItem.item_name, literal_column("',\n'")))
                                              .join(EventItem, isouter=True)
                                              .group_by(event_participation_repo.EventSpecification.event_year, event_participation_repo.EventSpecification.event_week)
                                              .order_by(event_participation_repo.EventSpecification.event_year.desc(), event_participation_repo.EventSpecification.event_week.desc())
                                              .limit(limit))
  return result.all()

async def get_event_item_stats(session, start_year: Optional[int]=None, end_year: Optional[int]=None) -> List[Tuple[str, int, str]]:
  final_stats = []

  filters = []
  if start_year is not None:
    filters.append(event_participation_repo.EventSpecification.event_year >= start_year)
  if end_year is not None:
    filters.append(event_participation_repo.EventSpecification.event_year <= end_year)

  counts_data = (await run_query_in_thread(session, select(EventItem.item_name, func.count(EventItem.item_name))
                                                    .join(event_participation_repo.EventSpecification)
                                                    .filter(*filters)
                                                    .group_by(EventItem.item_name)
                                                    .order_by(func.count(EventItem.item_name).desc(), EventItem.item_name))).all()
  for item_name, count in counts_data:
    last_ocurance = (await run_query_in_thread(session, select(event_participation_repo.EventSpecification.event_year, event_participation_repo.EventSpecification.event_week)
                                                        .join(EventItem)
                                                        .filter(EventItem.item_name == item_name, *filters)
                                                        .order_by(event_participation_repo.EventSpecification.event_year.desc(), event_participation_repo.EventSpecification.event_week.desc()))).first()

    if start_year is not None and end_year is not None and start_year == end_year:
      final_stats.append((item_name, count, f"{last_ocurance[1]}"))
    else:
      final_stats.append((item_name, count, f"{last_ocurance[0]} {last_ocurance[1]}"))

  return final_stats