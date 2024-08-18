from sqlalchemy import Column, Integer, Date
import datetime

import database
from database import dt_user_repo, dt_guild_repo, run_commit_in_thread

class DTActiveEntitiesData(database.base):
  __tablename__ = "dt_active_entities_statistics"

  date = Column(Date, primary_key=True)
  active_guilds = Column(Integer, nullable=False)
  active_users = Column(Integer, nullable=False)
  all_guilds = Column(Integer, nullable=False)
  all_users = Column(Integer, nullable=False)

  @classmethod
  async def generate(cls, session, today: datetime.date):
    item = cls(date=today,
               active_guilds=(await dt_guild_repo.get_number_of_active_guilds(session)),
               active_users=(await dt_user_repo.get_number_of_active_users(session)),
               all_guilds=(await dt_guild_repo.get_number_of_all_guilds(session)),
               all_users=(await dt_user_repo.get_number_of_all_users(session)))
    session.add(item)
    await run_commit_in_thread(session)
    return item

  async def update(self, session):
    self.active_guilds = (await dt_guild_repo.get_number_of_active_guilds(session))
    self.active_users = (await dt_user_repo.get_number_of_active_users(session))
    self.all_guilds = (await dt_guild_repo.get_number_of_all_guilds(session))
    self.all_users = (await dt_user_repo.get_number_of_all_users(session))
    await run_commit_in_thread(session)
