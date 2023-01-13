from sqlalchemy import Column, String, Integer, Boolean
from sqlalchemy.orm import relationship

from database import database, BigIntegerType

class DTGuild(database.base):
  __tablename__ = "dt_guilds"

  id = Column(BigIntegerType, primary_key=True)
  name = Column(String, index=True)
  level = Column(Integer)

  is_active = Column(Boolean, default=True)

  members = relationship("DTGuildMember", uselist=True, back_populates="guild")
  active_members = relationship("DTGuildMember", primaryjoin="and_(DTGuild.id==DTGuildMember.dt_guild_id, DTGuildMember.current_member==True)", uselist=True, viewonly=True)
  event_participations = relationship("EventParticipation", uselist=True, back_populates="dt_guild")
