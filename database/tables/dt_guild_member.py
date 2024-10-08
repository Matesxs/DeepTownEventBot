from sqlalchemy import Column, ForeignKey, DateTime, func
from sqlalchemy.orm import relationship

import database

class DTGuildMember(database.base):
  __tablename__ = "dt_guild_members"

  dt_user_id = Column(database.BigIntegerType, ForeignKey("dt_users.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
  dt_guild_id = Column(database.BigIntegerType, ForeignKey("dt_guilds.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
  created_at = Column(DateTime, nullable=False, default=func.now())

  user = relationship("DTUser", uselist=False, back_populates="members")
  guild = relationship("DTGuild", uselist=False, back_populates="members")

  event_participations = relationship("EventParticipation", primaryjoin="and_(foreign(DTGuildMember.dt_user_id)==EventParticipation.dt_user_id, foreign(DTGuildMember.dt_guild_id)==EventParticipation.dt_guild_id)", uselist=True, viewonly=True)
