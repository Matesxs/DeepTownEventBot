import disnake
from typing import Optional, Union
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship

import database
from features.base_bot import BaseAutoshardedBot

class DiscordUser(database.base):
  __tablename__ = "discord_users"

  id = Column(String, primary_key=True)
  name = Column(String, nullable=False, index=True)

  @classmethod
  def from_user(cls, user: Union[disnake.Member, disnake.User]):
    return cls(id=user.id, name=user.name)

  def update(self, user: Union[disnake.Member, disnake.User]):
    self.name = user.name

  async def to_object(self, bot: BaseAutoshardedBot) -> Optional[disnake.User]:
    user = bot.get_user(int(self.id))
    if user is None:
      user = await bot.fetch_user(int(self.id))
    return user

class DiscordGuild(database.base):
  __tablename__ = "discord_guilds"

  id = Column(String, primary_key=True)
  name = Column(String, nullable=False, index=True)

  admin_role_id = Column(String, nullable=True)

  tracking_settings = relationship("TrackingSettings", uselist=True, back_populates="guild")
  lotteries = relationship("DTEventItemLottery", uselist=True, back_populates="guild")

  @classmethod
  def from_guild(cls, guild: disnake.Guild):
    return cls(id=str(guild.id), name=guild.name)

  def update(self, guild: disnake.Guild):
    self.name = guild.name

  async def to_object(self, bot: BaseAutoshardedBot) -> Optional[disnake.Guild]:
    guild = bot.get_guild(int(self.id))
    if guild is None:
      try:
        guild = await bot.fetch_guild(int(self.id))
      except disnake.NotFound:
        return None
    return guild