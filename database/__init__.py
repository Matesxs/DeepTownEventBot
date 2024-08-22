import asyncio
from typing import Any
from sqlalchemy import BigInteger, create_engine
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
  engine = create_engine(config.base.database_connect_string, pool_pre_ping=True, pool_use_lifo=True, pool_size=5, max_overflow=10, pool_recycle=3600)
except Exception:
  logger.error(f"Failed to create database connection\n{traceback.format_exc()}")
  exit(-1)

logger.info("Database opened")

try:
  session_maker = sessionmaker(engine, expire_on_commit=False)
except Exception:
  logger.error(f"Failed to create database session maker\n{traceback.format_exc()}")
  exit(-1)

async def run_query_in_thread(session: Session, statement: Any, commit: bool=False):
  result = await asyncio.to_thread(session.execute, statement)
  if commit:
    await run_commit_in_thread(session)
  return result

async def run_commit_in_thread(session: Session):
  await asyncio.to_thread(session.commit)

async def add_items(session: Session, items):
  for item in items:
    session.add(item)
  await run_commit_in_thread(session)
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

  with session_maker() as session:
    base.metadata.create_all(engine)
    session.commit()

  logger.info("Initializating all loaded tables")