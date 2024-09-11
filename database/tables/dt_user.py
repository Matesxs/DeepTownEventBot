import datetime

from sqlalchemy import Column, String, Integer, DateTime, func
from sqlalchemy.orm import relationship

import database
from config import config
from utils.dt_helpers import DTUserData

class DTUser(database.base):
  __tablename__ = "dt_users"

  id = Column(database.BigIntegerType, primary_key=True)
  username = Column(String, index=True, default="*Unknown*")
  level = Column(Integer, default=-1)
  depth = Column(Integer, default=-1)
  last_online = Column(DateTime, nullable=True)
  created_at = Column(DateTime, nullable=False, default=func.now())

  mines = Column(Integer, default=0)
  chem_mines = Column(Integer, default=0)
  oil_mines = Column(Integer, default=0)
  crafters = Column(Integer, default=0)
  smelters = Column(Integer, default=0)
  jewel_stations = Column(Integer, default=0)
  chem_stations = Column(Integer, default=0)
  green_houses = Column(Integer, default=0)

  members = relationship("DTGuildMember", back_populates="user", uselist=True)
  event_participations = relationship("EventParticipation", back_populates="dt_user", uselist=True)

  @property
  def is_active(self) -> bool:
    return self.last_online + datetime.timedelta(days=config.data_manager.activity_days_threshold) > datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

  @classmethod
  def from_DTUserData(cls, data: DTUserData):
    return cls(
      id=data.id,
      username=data.name,
      level=data.level,
      depth=data.depth,
      last_online=data.last_online,
      mines=data.mines,
      chem_mines=data.chem_mines,
      oil_mines=data.oil_mines,
      crafters=data.crafters,
      smelters=data.smelters,
      jewel_stations=data.jewel_stations,
      chem_stations=data.chem_stations,
      green_houses=data.green_houses)

  def update(self, data: DTUserData):
    self.username = data.name
    self.level = data.level
    self.depth = data.depth
    self.last_online = data.last_online

    self.mines = data.mines
    self.chem_mines = data.chem_mines
    self.oil_mines = data.oil_mines
    self.crafters = data.crafters
    self.smelters = data.smelters
    self.jewel_stations = data.jewel_stations
    self.chem_stations = data.chem_stations
    self.green_houses = data.green_houses
