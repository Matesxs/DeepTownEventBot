from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.orm import relationship

from database import database, BigIntegerType
from utils.dt_helpers import DTUserData

class DTUser(database.base):
  __tablename__ = "dt_users"

  id = Column(BigIntegerType, primary_key=True)
  username = Column(String, index=True)
  level = Column(Integer)
  depth = Column(Integer)
  last_online = Column(DateTime, nullable=True)

  donated = Column(BigIntegerType, default=0)
  received = Column(BigIntegerType, default=0)

  mines = Column(Integer, default=0)
  chem_mines = Column(Integer, default=0)
  oil_mines = Column(Integer, default=0)
  crafters = Column(Integer, default=0)
  smelters = Column(Integer, default=0)
  jewel_stations = Column(Integer, default=0)
  chem_stations = Column(Integer, default=0)
  green_houses = Column(Integer, default=0)

  active_member = relationship("DTGuildMember", primaryjoin="and_(DTUser.id==DTGuildMember.dt_user_id, DTGuildMember.current_member==True)", uselist=False, viewonly=True)
  members = relationship("DTGuildMember", back_populates="user", uselist=True)
  event_participations = relationship("EventParticipation", back_populates="dt_user", uselist=True)

  @classmethod
  def from_DTUserData(cls, data: DTUserData):
    return cls(
      id=data.id,
      username=data.name,
      level=data.level,
      depth=data.depth,
      last_online=data.last_online,
      donated=data.donated,
      received=data.received,
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

    if data.donated != -1:
      self.donated = data.donated
    if data.received != -1:
      self.received = data.received

    self.mines = data.mines
    self.chem_mines = data.chem_mines
    self.oil_mines = data.oil_mines
    self.crafters = data.crafters
    self.smelters = data.smelters
    self.jewel_stations = data.jewel_stations
    self.chem_stations = data.chem_stations
    self.green_houses = data.green_houses
