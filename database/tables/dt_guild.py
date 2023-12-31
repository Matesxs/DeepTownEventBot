from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship

import database

class DTGuild(database.base):
  __tablename__ = "dt_guilds"

  id = Column(database.BigIntegerType, primary_key=True)
  name = Column(String, index=True)
  level = Column(Integer)

  is_active = Column(Boolean, index=True, default=True)

  members = relationship("DTGuildMember", uselist=True, back_populates="guild")
  event_participations = relationship("EventParticipation", uselist=True, back_populates="dt_guild")
