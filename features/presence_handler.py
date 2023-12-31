import disnake
import asyncio
from typing import Optional, List

from utils.logger import setup_custom_logger
from database import dt_guild_repo, dt_guild_member_repo

logger = setup_custom_logger(__name__)

class InfiniteLooper:
  def __init__(self, data: List):
    self.data = data
    self.length = len(data)
    self.cntr = 0

  def get(self):
    if self.length == 0:
      return None

    ret = self.data[self.cntr]
    self.cntr = (self.cntr + 1) % self.length
    return ret

class MissingHandler(dict):
  def __missing__(self, key):
    return "{" + key + "}"

class PresenceHandler:
  def __init__(self, bot, messages: List[str], cycle_interval_s: float, loop: Optional[asyncio.AbstractEventLoop] = None):
    self.bot = bot
    self.task: Optional[asyncio.Task] = None
    self.loop = loop if loop is not None else asyncio.get_event_loop()

    self.messages = InfiniteLooper(messages)
    self.cycle_interval = cycle_interval_s
    self.last_message = None

  def start(self):
    if self.task is None:
      self.task = self.loop.create_task(self.runner())

  def stop(self):
    if self.task is not None:
      self.task.cancel()

    self.task = None
    self.last_message = None

  def set_messages(self, messages: List[str]):
    self.messages = InfiniteLooper(messages)

  async def handle_buildin_data_replacement(self, string: str):
    if "{guilds}" in string:
      string = string.format_map(MissingHandler(guilds=len(self.bot.guilds)))

    if "{users}" in string:
      string = string.format_map(MissingHandler(users=len(self.bot.users)))

    if "{dt_guilds}" in string:
      string = string.format_map(MissingHandler(dt_guilds=(await dt_guild_repo.get_number_of_active_guilds())))

    if "{dt_users}" in string:
      string = string.format_map(MissingHandler(dt_users=(await dt_guild_member_repo.get_number_of_active_members())))

    return string

  async def runner(self):
    while True:
      if self.bot.is_ready():
        message = self.messages.get()
        message = await self.handle_buildin_data_replacement(message)
        # logger.info(f"New status: {message}")

        if message is not None and (self.last_message is None or message != self.last_message):
          try:
            await self.bot.change_presence(activity=disnake.Game(name=message, type=0), status=disnake.Status.online)
            self.last_message = message
          except asyncio.CancelledError:
            break
          except:
            pass

        await asyncio.sleep(self.cycle_interval)
      else:
        await asyncio.sleep(1)
