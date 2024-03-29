import datetime
from sqlalchemy import Column, ForeignKey, Integer, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship

import database
from utils.dt_helpers import DTUserData

class EventSpecification(database.base):
  __tablename__ = "event_specifications"
  __table_args__ = (UniqueConstraint('event_year', 'event_week'),)

  event_id = Column(database.BigIntegerType, primary_key=True, autoincrement=True)

  event_year = Column(Integer, index=True, nullable=False)
  event_week = Column(Integer, index=True, nullable=False)

  participation_items = relationship("EventItem", uselist=True, back_populates="event_specification")
  event_participations = relationship("EventParticipation", uselist=True, back_populates="event_specification")

class EventParticipation(database.base):
  __tablename__ = "event_participations"

  event_id = Column(database.BigIntegerType, ForeignKey("event_specifications.event_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
  dt_guild_id = Column(database.BigIntegerType, ForeignKey("dt_guilds.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
  dt_user_id = Column(database.BigIntegerType, ForeignKey("dt_users.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
  updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, index=True, nullable=False)

  event_specification = relationship("EventSpecification", uselist=False, back_populates="event_participations")
  dt_user = relationship("DTUser", uselist=False, back_populates="event_participations")
  dt_guild = relationship("DTGuild", uselist=False, back_populates="event_participations")

  amount = Column(database.BigIntegerType, default=0, index=True, nullable=False)

  def to_DTUserData(self) -> DTUserData:
    return DTUserData(self.dt_user.username,
                      self.dt_user_id,
                      self.dt_user.level,
                      self.dt_user.depth,
                      self.dt_user.last_online,
                      self.amount,
                      self.dt_user.mines,
                      self.dt_user.chem_mines,
                      self.dt_user.oil_mines,
                      self.dt_user.crafters,
                      self.dt_user.smelters,
                      self.dt_user.jewel_stations,
                      self.dt_user.chem_stations,
                      self.dt_user.green_houses)
