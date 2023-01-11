import asyncio
import datetime
import dataclasses
from typing import List, Optional, Tuple
import traceback
from aiohttp.client_exceptions import InvalidURL

from config import config
from features.base_bot import BaseAutoshardedBot
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
  received: int
  donated: int

  mines: int=0
  chem_mines: int=0
  oil_mines: int=0
  crafters: int=0
  smelters: int=0
  jewel_stations: int=0
  chem_stations: int=0
  green_houses: int=0

  @classmethod
  def from_api_data(cls, guild_data: dict, donations: tuple):
    return cls(
      guild_data[1] if guild_data[1] is not None else "*Unknown*", guild_data[0], guild_data[3], guild_data[4], datetime.datetime.strptime(guild_data[2], '%a, %d %b %Y %H:%M:%S GMT'),
      guild_data[-1], donations[1], donations[0],
      guild_data[5], guild_data[6], guild_data[7], guild_data[8], guild_data[9], guild_data[10], guild_data[11], guild_data[12]
    )

  def __repr__(self):
    return f"<{self.name}({self.id}),{self.level},{self.depth},'{self.last_online if self.last_online is not None else '*Never*'}', {self.donated}, {self.received},{self.last_event_contribution}, ({self.mines},{self.chem_mines},{self.oil_mines},{self.crafters},{self.smelters},{self.jewel_stations},{self.chem_stations},{self.green_houses})>"

@dataclasses.dataclass
class DTGuildData:
  name: str
  id: int
  level: int
  players: List[DTUserData]

  def __repr__(self):
    return f"<{self.name}({self.id}),{self.level}(\n\t" + "\n\t".join([str(p) for p in self.players]) + "\n)>"

def get_event_index(date:datetime.datetime):
  event_year = date.year
  week_number = date.isocalendar()[1]

  if date.month == 1 and week_number > 5:
    event_year -= 1

  if date.weekday() < 3 or (date.weekday() == 3 and date.hour < 8):
    week_number -= 1

  if week_number <= 0:
    event_year -= 1
    week_number = datetime.date(event_year, 12, 28).isocalendar()[1]

  return event_year, week_number

async def get_dt_guild_data(bot: BaseAutoshardedBot, guild_id:int) -> Optional[DTGuildData]:
  async with bot.http_session.get(f"http://dtat.hampl.space/data/donations/current/guild/id/{guild_id}") as response:
    if response.status != 200:
      return None

    try:
      donations_data = await response.json(content_type="text/html")
      donations_data = {d[0]: (d[1], d[2]) for d in donations_data["data"]}
    except Exception:
      logger.error(traceback.format_exc())
      return None

  await asyncio.sleep(0.1)

  async with bot.http_session.get(f"http://dtat.hampl.space/data/guild/id/{guild_id}/data") as response:
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
    player_donations = donations_data[player_data[1]] if player_data[1] in donations_data.keys() else (-1, -1)
    players.append(DTUserData.from_api_data(player_data, player_donations))

  return DTGuildData(guild_data_json["name"] if guild_data_json["name"] is not None else "*Unknown*", guild_data_json["id"], guild_data_json["level"], players)

async def get_ids_of_all_guilds(bot: BaseAutoshardedBot) -> Optional[List[int]]:
  async with bot.http_session.get("http://dtat.hampl.space/data/guild/name") as response:
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

async def get_guild_info(bot: BaseAutoshardedBot, guild_name: Optional[str]=None) -> Optional[List[Tuple[int, str, int]]]:
  try:
    async with bot.http_session.get("http://dtat.hampl.space/data/guild/name" + ("" if guild_name is None else f"/{guild_name.replace(' ', '_')}")) as response:
      if response.status != 200:
        return None

      try:
        json_data = await response.json(content_type="text/html")
      except Exception:
        logger.error(traceback.format_exc())
        return None

      data = []
      for guild_data in json_data["data"]:
        data.append(tuple(guild_data))
      return data
  except InvalidURL:
    return None
