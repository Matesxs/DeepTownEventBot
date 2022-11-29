from sqlalchemy import Column, String, Integer
from sqlalchemy.orm import relationship

from database import database, BigIntegerType

class DTGuild(database.base):
  __tablename__ = "dt_guilds"

  id = Column(BigIntegerType, primary_key=True)
  name = Column(String, index=True)
  level = Column(Integer)

  members = relationship("DTGuildMember", uselist=True, back_populates="guild")
  event_participations = relationship("EventParticipation", uselist=True, back_populates="dt_guild")
