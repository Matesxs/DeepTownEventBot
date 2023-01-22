from typing import Optional, List

from sqlalchemy import select, delete

from database import run_query, run_commit, session
from database.tables.dt_blacklist import BlacklistType, DTBlacklistItem

async def get_blacklist_item(bl_type: BlacklistType, identifier: int) -> Optional[DTBlacklistItem]:
  statement = select(DTBlacklistItem).filter(DTBlacklistItem.bl_type == BlacklistType(bl_type), DTBlacklistItem.identifier == identifier)
  result = await run_query(statement)
  return result.scalar_one_or_none()

async def is_on_blacklist(bl_type: BlacklistType, identifier: int) -> bool:
  result = await run_query(select(DTBlacklistItem.identifier).filter(DTBlacklistItem.bl_type == BlacklistType(bl_type), DTBlacklistItem.identifier == identifier))
  return result.scalar_one_or_none() is not None

async def get_blacklist_items(bl_type: Optional[BlacklistType]=None) -> List[DTBlacklistItem]:
  if bl_type is not None:
    result = await run_query(select(DTBlacklistItem).filter(DTBlacklistItem.bl_type == BlacklistType(bl_type)))
    return result.scalars().all()

  result = await run_query(select(DTBlacklistItem))
  return result.scalars().all()

async def create_blacklist_item(bl_type: BlacklistType, identifier: int, additional_data: Optional[str]=None) -> Optional[DTBlacklistItem]:
  item = await get_blacklist_item(bl_type, identifier)
  if item is not None: return None

  item = DTBlacklistItem(bl_type=BlacklistType(bl_type), identifier=identifier, additional_data=additional_data)
  session.add(item)
  await run_commit()
  return item

async def remove_blacklist_item(bl_type: BlacklistType, identifier: int) -> bool:
  result = await run_query(delete(DTBlacklistItem).filter(DTBlacklistItem.bl_type == BlacklistType(bl_type), DTBlacklistItem.identifier == identifier))
  await run_commit()
  return result.rowcount > 0
