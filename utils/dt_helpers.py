import asyncio
import datetime
import dataclasses
from typing import List, Optional, Tuple
import traceback
from aiohttp import ClientSession, ClientTimeout

from config import config
from utils.logger import setup_custom_logger

logger = setup_custom_logger(__name__)

@dataclasses.dataclass
class DTUserData:
  name: str
  id: int
  level: int
  depth: int
  last_online: Optional[datetime.datetime]

  last_event_contribution: int

  mines: int=0
  chem_mines: int=0
  oil_mines: int=0
  crafters: int=0
  smelters: int=0
  jewel_stations: int=0
  chem_stations: int=0
  green_houses: int=0

  @classmethod
  def from_api_data(cls, guild_data: dict):
    return cls(
      guild_data[1] if guild_data[1] is not None else "*Unknown*", guild_data[0], guild_data[3], guild_data[4], datetime.datetime.strptime(guild_data[2], '%a, %d %b %Y %H:%M:%S GMT'),
      guild_data[-1],
      guild_data[5], guild_data[6], guild_data[7], guild_data[8], guild_data[9], guild_data[10], guild_data[11], guild_data[12]
    )

  @property
  def is_active(self):
    return self.last_online + datetime.timedelta(days=config.data_manager.activity_days_threshold) > datetime.datetime.utcnow()

  def __repr__(self):
    return f"<{self.name}({self.id}),{self.level},{self.depth},'{self.last_online if self.last_online is not None else '*Never*'}',{self.last_event_contribution}, ({self.mines},{self.chem_mines},{self.oil_mines},{self.crafters},{self.smelters},{self.jewel_stations},{self.chem_stations},{self.green_houses})>"

@dataclasses.dataclass
class DTGuildData:
  name: str
  id: int
  level: int
  players: List[DTUserData]

  @property
  def is_active(self):
    for player in self.players:
      if player.is_active:
        return True
    return False

  def __repr__(self):
    return f"<{self.name}({self.id}),{self.level}(\n\t" + "\n\t".join([str(p) for p in self.players]) + "\n)>"

def get_event_index(date:datetime.datetime):
  event_year = date.year
  week_number = date.isocalendar()[1]

  if date.month == 1 and week_number > 5:
    event_year -= 1

  if (date.weekday() < config.event_tracker.event_start_day or
      (date.weekday() == config.event_tracker.event_start_day and date.hour < config.event_tracker.event_start_hour) or
      (date.weekday() == config.event_tracker.event_start_day and date.hour == config.event_tracker.event_start_hour and date.minute < config.event_tracker.event_start_minute)):
    week_number -= 1

  if week_number <= 0:
    event_year -= 1
    week_number = datetime.date(event_year, 12, 28).isocalendar()[1]

  return event_year, week_number

def event_index_to_date_range(year: int, week: int) -> Tuple[datetime.datetime, datetime.datetime]:
  date_string = f"{year}-{week}-4"
  start_date = datetime.datetime.strptime(date_string, "%Y-%W-%w").replace(hour=config.event_tracker.event_start_hour, minute=config.event_tracker.event_start_minute)
  return start_date, start_date + datetime.timedelta(days=4)

async def get_dt_guild_data(guild_id:int, update: bool=False) -> Optional[DTGuildData]:
  async with ClientSession(timeout=ClientTimeout(total=60)) as session:
    if update:
      async with session.get(f"http://dtat.hampl.space/data/donations/current/guild/id/{guild_id}") as response:
        if response.status != 200:
          return None

    await asyncio.sleep(0.1)

    async with session.get(f"http://dtat.hampl.space/data/guild/id/{guild_id}/data") as response:
      if response.status != 200:
        return None

      try:
        guild_data_json = await response.json(content_type="text/html")
      except Exception:
        logger.error(traceback.format_exc())
        return None

  if config.data_manager.ignore_empty_guilds:
    if len(guild_data_json["players"]["data"]) == 0:
      return None

  players = []
  for player_data in guild_data_json["players"]["data"]:
    players.append(DTUserData.from_api_data(player_data))

  return DTGuildData(guild_data_json["name"] if guild_data_json["name"] is not None else "*Unknown*", guild_data_json["id"], guild_data_json["level"], players)

async def get_ids_of_all_guilds() -> Optional[List[int]]:
  async with ClientSession(timeout=ClientTimeout(total=30)) as session:
    async with session.get("http://dtat.hampl.space/data/guild/name") as response:
      if response.status != 200:
        return None

      try:
        json_data = await response.json(content_type="text/html")
      except Exception:
        logger.error(traceback.format_exc())
        return None

  ids = []
  for guild_data in json_data["data"]:
    ids.append(guild_data[0])
  return ids
