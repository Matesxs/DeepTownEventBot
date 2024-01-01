from sqlalchemy import Column, Integer, DateTime
import datetime

import database
from database import dt_user_repo, dt_guild_repo

class DTActiveEntitiesData(database.base):
  __tablename__ = "dt_active_entities_statistics"

  id = Column(database.BigIntegerType, primary_key=True, autoincrement=True)

  date = Column(DateTime, default=datetime.datetime.utcnow, index=True)
  active_guilds = Column(Integer, nullable=False)
  active_users = Column(Integer, nullable=False)
  all_guilds = Column(Integer, nullable=False)
  all_users = Column(Integer, nullable=False)

  @classmethod
  async def generate(cls):
    item = cls(active_guilds=(await dt_guild_repo.get_number_of_active_guilds()),
               active_users=(await dt_user_repo.get_number_of_active_users()),
               all_guilds=(await dt_guild_repo.get_number_of_all_guilds()),
               all_users=(await dt_user_repo.get_number_of_all_users()))
    await database.add_item(item)
    await database.run_commit()
    return item
