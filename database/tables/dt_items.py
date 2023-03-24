import enum
from sqlalchemy import Column, ForeignKey, String, Float, Integer, Enum
from sqlalchemy.orm import relationship, Mapped
from typing import List
import math

import database

class DTItemComponentMapping(database.base):
  __tablename__ = "dt_item_component_mapping"

  target_item_name = Column(ForeignKey("dt_items.name", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
  component_item_name = Column(ForeignKey("dt_items.name", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)

  component:Mapped["DTItem"] = relationship("DTItem", primaryjoin="DTItemComponentMapping.component_item_name==DTItem.name", uselist=False)
  amount = Column(Float, default=0)

class ItemType(enum.Enum):
  RAW = 0
  CRAFTABLE = 1

  def __str__(self):
    return self.name

class ItemSource(enum.Enum):
  MINING = 0
  CHEM_MINING = 1
  OIL_MINING = 2
  WATER_COLLECTOR = 3
  URANIUM_ENRICHMENT = 4
  CRAFTING = 5
  SMELTING = 6
  CHEMISTRY = 7
  JEWEL_CRAFTING = 8
  GREENHOUSE = 9
  BUY = 10
  OTHER = 11

  def __str__(self):
    return self.name

class DTItem(database.base):
  __tablename__ = "dt_items"

  name = Column(String, primary_key=True)
  item_type = Column(Enum(ItemType))
  item_source = Column(Enum(ItemSource))
  value = Column(Float, default=0)
  crafting_time = Column(Float, default=0)
  crafting_batch_size = Column(Integer, default=1)

  components_data:Mapped[List[DTItemComponentMapping]] = relationship("DTItemComponentMapping", primaryjoin="DTItem.name==DTItemComponentMapping.target_item_name", uselist=True)

  @property
  def cumulative_crafting_time_per_item(self) -> float:
    if self.item_type == ItemType.CRAFTABLE:
      crafting_time = self.crafting_time / self.crafting_batch_size

      for component_data in self.components_data:
        crafting_time += (component_data.component.cumulative_crafting_time_per_item * component_data.amount)

      return crafting_time
    return 0

  @property
  def component_value(self) -> float:
    value = 0
    if self.item_type == ItemType.CRAFTABLE:
      for component_data in self.components_data:
        value += (component_data.component.value * component_data.amount)

    return value

  @property
  def material_efficiency(self) -> float:
    if self.item_type == ItemType.CRAFTABLE:
      return self.value / self.component_value
    else:
      return 1.0

  @property
  def cumulative_material_efficency(self) -> float:
    efficiency = self.material_efficiency

    if self.item_type == ItemType.CRAFTABLE:
      for component_data in self.components_data:
        efficiency *= component_data.component.material_efficiency

    return efficiency

  def __repr__(self):
    return f"{self.name}: {self.value}"

class EventItem(database.base):
  __tablename__ = "event_items"

  event_id = Column(database.BigIntegerType, ForeignKey("event_specifications.event_id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
  item_name = Column(String, ForeignKey("dt_items.name", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
  base_amount = Column(Integer)

  item = relationship("DTItem", uselist=False)
  event_specification = relationship("EventSpecification", uselist=False, back_populates="participation_items")

  def get_event_amount_scaling(self, levels: int=30):
    if self.base_amount is None: return None
    levels = max(levels, 1)
    return [self.base_amount, *[math.floor(self.base_amount * 0.9202166811 * math.exp(level / 8)) for level in range(2, levels + 1)]]

  def get_event_amount_sum(self, levels: int=30):
    amounts = self.get_event_amount_scaling(levels)
    if amounts is None: return None
    return sum(amounts)
