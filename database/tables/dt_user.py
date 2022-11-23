from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

from database import database, BigIntegerType

class DTUser(database.base):
  __tablename__ = "dt_users"

  id = Column(BigIntegerType, primary_key=True)
  username = Column(String, nullable=False, index=True)

  members = relationship("DTGuildMember", back_populates="user")
