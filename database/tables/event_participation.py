from sqlalchemy import Column, ForeignKey, Integer
from sqlalchemy.orm import relationship

from database import database, BigIntegerType
from utils.dt_helpers import DTUserData

class EventParticipation(database.base):
  __tablename__ = "event_participations"

  year = Column(Integer, primary_key=True)
  event_week = Column(Integer, primary_key=True)
  dt_guild_id = Column(BigIntegerType, ForeignKey("dt_guilds.id", ondelete="CASCADE"), primary_key=True)
  dt_user_id = Column(BigIntegerType, ForeignKey("dt_users.id", ondelete="CASCADE"), primary_key=True)

  dt_user = relationship("DTUser", uselist=False, back_populates="event_participations")
  dt_guild = relationship("DTGuild", uselist=False, back_populates="event_participations")

  amount = Column(BigIntegerType, default=0)

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
