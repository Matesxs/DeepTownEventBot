import enum
from sqlalchemy import Column, Enum, Integer, String

from database import database

class BlacklistType(enum.Enum):
  USER = 1
  GUILD = 2

  def __str__(self):
    return self.name

class DTBlacklistItem(database.base):
  __tablename__ = "dt_blacklist"

  bl_type = Column(Enum(BlacklistType), primary_key=True)
  identifier = Column(Integer, primary_key=True)
  additional_data = Column(String, nullable=True)
