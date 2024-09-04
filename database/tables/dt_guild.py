from sqlalchemy import Column, String, Integer, Boolean, DateTime, func
from sqlalchemy.orm import relationship

import database
from utils.dt_helpers import DTGuildData

class DTGuild(database.base):
  __tablename__ = "dt_guilds"

  id = Column(database.BigIntegerType, primary_key=True)
  name = Column(String, index=True)
  level = Column(Integer)
  created_at = Column(DateTime, nullable=False, default=func.now())

  is_active = Column(Boolean, index=True, default=True)

  members = relationship("DTGuildMember", uselist=True, back_populates="guild")
  event_participations = relationship("EventParticipation", uselist=True, back_populates="dt_guild")

  def update(self, data: DTGuildData):
    self.name = data.name
    self.level = data.level
    self.is_active = data.is_active
