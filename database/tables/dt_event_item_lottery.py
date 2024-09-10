import datetime
import disnake
from typing import Optional, Union, List
from sqlalchemy import String, Integer, ForeignKey, Column, UniqueConstraint, DateTime, Boolean, select
from sqlalchemy.orm import relationship, Mapped

import database
from database import event_participation_repo
from utils import object_getters
from features.base_bot import BaseAutoshardedBot
from utils import dt_helpers

class DTEventItemLotteryGuessedItem(database.base):
  __tablename__ = "dt_event_item_lotery_guessed_items"

  guess_id = Column(database.BigIntegerType, ForeignKey("dt_event_item_lottery_guesses.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
  item_name = Column(String, ForeignKey("dt_items.name", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)

class DTEventItemLotteryGuess(database.base):
  __tablename__ = "dt_event_item_lottery_guesses"
  __table_args__ = (UniqueConstraint('guild_id', 'author_id', "event_id"),)

  id = Column(database.BigIntegerType, primary_key=True, autoincrement=True)
  created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

  event_id = Column(database.BigIntegerType, ForeignKey("event_specifications.event_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
  guild_id = Column(String, ForeignKey("discord_guilds.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)
  author_id = Column(String, ForeignKey("discord_users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)

  guessed_lotery_items: Mapped[List[DTEventItemLotteryGuessedItem]] = relationship("DTEventItemLotteryGuessedItem", uselist=True)
  event_specification = relationship("EventSpecification", uselist=False)
  user = relationship("DiscordUser", uselist=False)
  member = relationship("DiscordMember", uselist=False, primaryjoin="and_(foreign(DTEventItemLotteryGuess.guild_id) == DiscordMember.guild_id, foreign(DTEventItemLotteryGuess.author_id) == DiscordMember.user_id)", viewonly=True)
  guild = relationship("DiscordGuild", uselist=False)

  async def get_author(self, bot: BaseAutoshardedBot) -> Optional[disnake.Member | disnake.User]:
    guild = await self.guild.to_object(bot)
    if guild is None: return None
    author = await object_getters.get_or_fetch_member(guild, int(self.author_id))
    if author is None:
      author = await object_getters.get_or_fetch_user(bot, int(self.author_id))
    return author

class DTEventItemLottery(database.base):
  __tablename__ = "dt_event_item_lotteries"
  __table_args__ = (UniqueConstraint('author_id', 'guild_id', "event_id"),)

  id = Column(database.BigIntegerType, primary_key=True, unique=True, index=True, autoincrement=True)

  author_id = Column(String, ForeignKey("discord_users.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)
  guild_id = Column(String, ForeignKey("discord_guilds.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False, index=True)

  lottery_channel_id = Column(String, nullable=True)
  lottery_message_id = Column(String, nullable=True)

  event_id = Column(database.BigIntegerType, ForeignKey("event_specifications.event_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
  created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
  closed_at = Column(DateTime, nullable=True, default=None)

  auto_repeat = Column(Boolean, nullable=False, default=False)
  split_rewards = Column(Boolean, nullable=False, default=False)
  autoping_winners = Column(Boolean, nullable=False, default=False)
  autoshow_guesses = Column(Boolean, nullable=False, default=False)

  guessed_4_reward_item_name = Column(String, ForeignKey("dt_items.name", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
  guessed_4_item_reward_amount = Column(Integer, default=0, nullable=False)
  guessed_3_reward_item_name = Column(String, ForeignKey("dt_items.name", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
  guessed_3_item_reward_amount = Column(Integer, default=0, nullable=False)
  guessed_2_reward_item_name = Column(String, ForeignKey("dt_items.name", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
  guessed_2_item_reward_amount = Column(Integer, default=0, nullable=False)
  guessed_1_reward_item_name = Column(String, ForeignKey("dt_items.name", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
  guessed_1_item_reward_amount = Column(Integer, default=0, nullable=False)

  guild = relationship("DiscordGuild", uselist=False, back_populates="lotteries")
  user = relationship("DiscordUser", uselist=False)
  member = relationship("DiscordMember", uselist=False, primaryjoin="and_(foreign(DTEventItemLottery.guild_id) == DiscordMember.guild_id, foreign(DTEventItemLottery.author_id) == DiscordMember.user_id)", viewonly=True)
  guesses: Mapped[List[DTEventItemLotteryGuess]] = relationship("DTEventItemLotteryGuess", uselist=True, primaryjoin="and_(foreign(DTEventItemLottery.guild_id) == DTEventItemLotteryGuess.guild_id, foreign(DTEventItemLottery.event_id) == DTEventItemLotteryGuess.event_id)", viewonly=True)
  event_specification = relationship("EventSpecification", uselist=False)

  def get_lottery_message_url(self):
    return f"https://discord.com/channels/{self.guild_id}/{self.lottery_channel_id}/{self.lottery_message_id}"

  async def get_lotery_channel(self, bot: BaseAutoshardedBot) -> Optional[Union[disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable]]:
    if self.lottery_channel_id is None: return None
    guild = await self.guild.to_object(bot)
    if guild is None: return None
    channel = await object_getters.get_or_fetch_channel(guild, int(self.lottery_channel_id))
    if not isinstance(channel, (disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable)): return None
    return channel

  async def get_lotery_message(self, bot: BaseAutoshardedBot) -> Optional[disnake.Message]:
    if self.lottery_message_id is None: return None
    channel = await self.get_lotery_channel(bot)
    lotery_message = await object_getters.get_or_fetch_message(bot, channel, int(self.lottery_message_id))
    return lotery_message

  async def get_author(self, bot: BaseAutoshardedBot) -> Optional[disnake.Member | disnake.User]:
    guild = await self.guild.to_object(bot)
    if guild is None: return None
    author = await object_getters.get_or_fetch_member(guild, int(self.author_id))
    if author is None:
      author = await object_getters.get_or_fetch_user(bot, int(self.author_id))
    return author

  async def close(self, session):
    self.closed_at = datetime.datetime.now(datetime.UTC)
    await database.run_commit_in_thread(session)

  async def repeat(self, session):
    next_year, next_week = dt_helpers.get_event_index(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=7))
    event_specification = await event_participation_repo.get_or_create_event_specification(session, next_year, next_week)

    self.event_id = event_specification.event_id

    self.created_at = datetime.datetime.now(datetime.UTC)
    self.closed_at = None

    await database.run_commit_in_thread(session)

    self.event_specification = event_specification
