from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from database import database, BigIntegerType

class EventParticipation(database.base):
  __tablename__ = "event_participations"

  year = Column(Integer, primary_key=True)
  event_week = Column(Integer, primary_key=True)
  dt_guild_id = Column(BigIntegerType, ForeignKey("dt_guilds.id", ondelete="CASCADE"), primary_key=True)
  dt_user_id = Column(BigIntegerType, ForeignKey("dt_users.id", ondelete="CASCADE"), primary_key=True)

  ammount = Column(BigIntegerType, default=0)

  user = relationship("DTUser", uselist=False)
  member = relationship("DTGuildMember", primaryjoin="and_(EventParticipation.dt_user_id==DTGuildMember.dt_user_id, EventParticipation.dt_guild_id==DTGuildMember.dt_guild_id)", uselist=False, back_populates="event_participations")
