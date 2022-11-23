from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from database import database, BigIntegerType

class DTGuild(database.base):
  __tablename__ = "dt_guilds"

  id = Column(BigIntegerType, primary_key=True)
  name = Column(String, index=True)

  members = relationship("DTGuildMember", uselist=True, back_populates="guild")
  event_participations = relationship("EventParticipation", primaryjoin="DTGuild.id==EventParticipation.dt_guild_id", uselist=True)
