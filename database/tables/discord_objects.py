import disnake
from typing import Optional
from sqlalchemy import Column, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship

import database
from features.base_bot import BaseAutoshardedBot
from utils import object_getters

class DiscordUser(database.base):
  __tablename__ = "discord_users"

  id = Column(String, primary_key=True)
  name = Column(String, nullable=False, index=True)
  created_at = Column(DateTime, nullable=False)

  command_calls = relationship("CommandCallAuditlog", uselist=True, back_populates="author")

  @classmethod
  def from_user(cls, user: disnake.Member | disnake.User):
    return cls(id=str(user.id), name=user.name, created_at=user.created_at)

  def update(self, user: disnake.Member | disnake.User):
    name = user.global_name or user.name
    if self.name != name:
      self.name = name

    if self.created_at != user.created_at:
      self.created_at = user.created_at

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
  joined_at = Column(DateTime, nullable=True)

  user = relationship("DiscordUser", uselist=False)
  guild = relationship("DiscordGuild", uselist=False, back_populates="members")

  @classmethod
  def from_member(cls, member: disnake.Member):
    return cls(user_id=str(member.id), guild_id=str(member.guild.id), name=member.display_name, joined_at=member.joined_at)

  def update(self, member: disnake.Member):
    if self.name != member.display_name:
      self.name = member.display_name

    if self.joined_at != member.joined_at:
      self.joined_at = member.joined_at

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
  command_calls = relationship("CommandCallAuditlog", uselist=True, back_populates="guild")

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