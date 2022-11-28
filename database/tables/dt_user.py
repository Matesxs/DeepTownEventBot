from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.orm import relationship

from database import database, BigIntegerType

class DTUser(database.base):
  __tablename__ = "dt_users"

  id = Column(BigIntegerType, primary_key=True)
  username = Column(String, index=True)
  level = Column(Integer)
  depth = Column(Integer)
  last_online = Column(DateTime, nullable=True)

  members = relationship("DTGuildMember", back_populates="user")
