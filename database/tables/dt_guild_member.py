from sqlalchemy import Column, ForeignKey, Boolean
from sqlalchemy.orm import relationship

from database import database, BigIntegerType

class DTGuildMember(database.base):
  __tablename__ = "dt_guild_members"

  dt_user_id = Column(BigIntegerType, ForeignKey("dt_users.id", ondelete="CASCADE"), primary_key=True)
  dt_guild_id = Column(BigIntegerType, ForeignKey("dt_guilds.id", ondelete="CASCADE"), primary_key=True)
  current_member = Column(Boolean, index=True, default=True)

  user = relationship("DTUser", uselist=False, back_populates="members")
  guild = relationship("DTGuild", uselist=False, back_populates="members")
  other_memberships = relationship("DTGuildMember", primaryjoin="and_(dt_user_id==DTGuildMember.dt_user_id, dt_guild_id!=DTGuildMember.dt_guild_id, DTGuildMember.current_member==True)", uselist=True)

  event_participations = relationship("EventParticipation", primaryjoin="and_(DTGuildMember.dt_user_id==EventParticipation.dt_user_id, DTGuildMember.dt_guild_id==EventParticipation.dt_guild_id)", uselist=True, back_populates="member")
