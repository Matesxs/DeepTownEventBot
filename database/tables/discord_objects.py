import disnake
from typing import Optional, Union
from sqlalchemy import Column, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship

import database
from features.base_bot import BaseAutoshardedBot
from utils import object_getters

class DiscordUser(database.base):
  __tablename__ = "discord_users"

  id = Column(String, primary_key=True)
  name = Column(String, nullable=False, index=True)

  @classmethod
  def from_user(cls, user: Union[disnake.Member, disnake.User]):
    return cls(id=str(user.id), name=user.name)

  def update(self, user: Union[disnake.Member, disnake.User]):
    self.name = user.name

  async def to_object(self, bot: BaseAutoshardedBot) -> Optional[disnake.User]:
    user = bot.get_user(int(self.id))
    if user is None:
      user = await bot.fetch_user(int(self.id))
    return user

class DiscordMember(database.base):
  __tablename__ = "discord_members"

  user_id = Column(String, ForeignKey("discord_users.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
  guild_id = Column(String, ForeignKey("discord_guilds.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)

  name = Column(String, nullable=False, index=True)

  user = relationship("DiscordUser", uselist=False)
  guild = relationship("DiscordGuild", uselist=False, back_populates="members")

  @classmethod
  def from_member(cls, member: disnake.Member):
    return cls(user_id=str(member.id), guild_id=str(member.guild.id), name=member.display_name)

  def update(self, member: disnake.Member):
    self.name = member.display_name

  async def to_object(self, bot: BaseAutoshardedBot) -> Optional[disnake.Member]:
    guild = await self.guild.to_object(bot)
    if guild is None: return None
    return await object_getters.get_or_fetch_member(guild, int(self.user_id))

class DiscordGuild(database.base):
  __tablename__ = "discord_guilds"

  id = Column(String, primary_key=True)
  name = Column(String, nullable=False, index=True)

  admin_role_id = Column(String, nullable=True)

  enable_better_message_links = Column(Boolean, default=False, nullable=False)

  tracking_settings = relationship("TrackingSettings", uselist=True, back_populates="guild")
  lotteries = relationship("DTEventItemLottery", uselist=True, back_populates="guild")
  members = relationship("DiscordMember", uselist=True, back_populates="guild")

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