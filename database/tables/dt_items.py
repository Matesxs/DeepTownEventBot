from sqlalchemy import Column, ForeignKey, String, Float, Integer
from sqlalchemy.orm import relationship

from database import database, BigIntegerType

class DTItem(database.base):
  __tablename__ = "dt_items"

  name = Column(String, primary_key=True)
  value = Column(Float, nullable=False, default=0)

  def __repr__(self):
    return f"{self.name}: {self.value}"

class EventItem(database.base):
  __tablename__ = "event_items"

  event_id = Column(BigIntegerType, ForeignKey("event_specifications.event_id", ondelete="CASCADE"), primary_key=True)
  item_name = Column(String, ForeignKey("dt_items.name", ondelete="CASCADE"), primary_key=True)
  base_amount = Column(Integer, nullable=False, default=0)

  item = relationship("DTItem", uselist=False)
  event_specification = relationship("EventSpecification", uselist=False, back_populates="participation_items")
