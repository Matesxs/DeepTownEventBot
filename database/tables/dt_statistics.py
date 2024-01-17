from sqlalchemy import Column, Integer, Date
import datetime

import database
from database import dt_user_repo, dt_guild_repo

class DTActiveEntitiesData(database.base):
  __tablename__ = "dt_active_entities_statistics"

  date = Column(Date, primary_key=True)
  active_guilds = Column(Integer, nullable=False)
  active_users = Column(Integer, nullable=False)
  all_guilds = Column(Integer, nullable=False)
  all_users = Column(Integer, nullable=False)

  @classmethod
  async def generate(cls, today: datetime.date):
    item = cls(date=today,
               active_guilds=(await dt_guild_repo.get_number_of_active_guilds()),
               active_users=(await dt_user_repo.get_number_of_active_users()),
               all_guilds=(await dt_guild_repo.get_number_of_all_guilds()),
               all_users=(await dt_user_repo.get_number_of_all_users()))
    await database.add_item(item)
    return item

  async def update(self):
    self.active_guilds = (await dt_guild_repo.get_number_of_active_guilds())
    self.active_users = (await dt_user_repo.get_number_of_active_users())
    self.all_guilds = (await dt_guild_repo.get_number_of_all_guilds())
    self.all_users = (await dt_user_repo.get_number_of_all_users())
    await database.run_commit()
