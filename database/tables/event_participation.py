from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from database import database, BigIntegerType

class EventParticipation(database.base):
  __tablename__ = "event_participations"

  year = Column(Integer, primary_key=True)
  event_week = Column(Integer, primary_key=True)
  dt_guild_id = Column(BigIntegerType, ForeignKey("dt_guilds.id", ondelete="CASCADE"), primary_key=True)
  dt_user_id = Column(BigIntegerType, ForeignKey("dt_users.id", ondelete="CASCADE"), primary_key=True)

  dt_user = relationship("DTUser", uselist=False)
  dt_guild = relationship("DTGuild", uselist=False)

  amount = Column(BigIntegerType, default=0)
