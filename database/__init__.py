import asyncio
from typing import Any, Union
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.engine import Result, CursorResult
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects import postgresql, sqlite
import pkgutil
import importlib
import traceback

from config import config
from utils.logger import setup_custom_logger

logger = setup_custom_logger(__name__)

if config.base.database_connect_string is None or config.base.database_connect_string == "":
  logger.error("Database connect string is empty!")
  exit(-1)

try:
  base = declarative_base()
  engine = create_engine(config.base.database_connect_string)

except Exception:
  logger.error(f"Failed to create database connection\n{traceback.format_exc()}")
  exit(-1)

logger.info("Database opened")

try:
  session:Session = sessionmaker(engine, expire_on_commit=False)()
except Exception:
  logger.error(f"Failed to create database session\n{traceback.format_exc()}")
  exit(-1)

session_lock = asyncio.Lock()
async def run_query(statement: Any, commit: bool=False) -> Result:
  await session_lock.acquire()
  result = await asyncio.to_thread(session.execute, statement)
  if commit:
    await asyncio.to_thread(session.commit)
  session_lock.release()
  return result

async def run_commit():
  await session_lock.acquire()
  await asyncio.to_thread(session.commit)
  session_lock.release()

async def add_item(item):
  await session_lock.acquire()
  session.add(item)
  await asyncio.to_thread(session.commit)
  session_lock.release()
  return item

async def remove_item(item):
  await session_lock.acquire()
  session.delete(item)
  await asyncio.to_thread(session.commit)
  session_lock.release()
  return item

async def add_items(items):
  await session_lock.acquire()
  for item in items:
    session.add(item)
  await asyncio.to_thread(session.commit)
  session_lock.release()
  return items

BigIntegerType = BigInteger()
BigIntegerType = BigIntegerType.with_variant(postgresql.BIGINT(), 'postgresql')
BigIntegerType = BigIntegerType.with_variant(sqlite.INTEGER(), 'sqlite')

def load_sub_modules(module):
  package = importlib.import_module(module)
  for _, name, _ in pkgutil.iter_modules(package.__path__):
    importlib.import_module(f'{package.__name__}.{name}')

def init_tables():
  load_sub_modules("database.tables")

  base.metadata.create_all(engine)
  session.commit()

  logger.info("Initializating all loaded tables")