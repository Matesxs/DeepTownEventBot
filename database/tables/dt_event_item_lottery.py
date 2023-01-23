import datetime
import disnake
from typing import Optional, Union
from sqlalchemy import String, Integer, ForeignKey, Column, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship

import database
from database import event_participation_repo
from utils import object_getters
from features.base_bot import BaseAutoshardedBot
from utils import dt_helpers

class DTEventItemLotteryGuessedItem(database.base):
  __tablename__ = "dt_event_item_lotery_guessed_items"

  guess_id = Column(database.BigIntegerType, ForeignKey("dt_event_item_lottery_guesses.id", ondelete="CASCADE"), primary_key=True)
  item_name = Column(String, ForeignKey("dt_items.name", ondelete="CASCADE"), primary_key=True)

class DTEventItemLotteryGuess(database.base):
  __tablename__ = "dt_event_item_lottery_guesses"
  __table_args__ = (UniqueConstraint('guild_id', 'user_id', "event_id"),)

  id = Column(database.BigIntegerType, primary_key=True, autoincrement=True)

  event_id = Column(database.BigIntegerType, ForeignKey("event_specifications.event_id", ondelete="CASCADE"), nullable=False)
  guild_id = Column(String, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True)
  user_id = Column(String, nullable=False, index=True)

  guessed_lotery_items = relationship("DTEventItemLotteryGuessedItem", uselist=True)
  event_specification = relationship("EventSpecification", uselist=False)

class DTEventItemLottery(database.base):
  __tablename__ = "dt_event_item_lotteries"
  __table_args__ = (UniqueConstraint('author_id', 'guild_id', "event_id"),)

  id = Column(database.BigIntegerType, primary_key=True, unique=True, index=True, autoincrement=True)

  author_id = Column(String, nullable=False, index=True)

  guild_id = Column(String, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True)
  lottery_channel_id = Column(String, nullable=True)
  lottery_message_id = Column(String, nullable=True)

  event_id = Column(database.BigIntegerType, ForeignKey("event_specifications.event_id", ondelete="CASCADE"), nullable=False)
  closed_at = Column(DateTime, nullable=True, default=None)

  guessed_4_reward_item_name = Column(String, ForeignKey("dt_items.name", ondelete="SET NULL"), nullable=True)
  guessed_4_item_reward_amount = Column(Integer, default=0, nullable=False)
  guessed_3_reward_item_name = Column(String, ForeignKey("dt_items.name", ondelete="SET NULL"), nullable=True)
  guessed_3_item_reward_amount = Column(Integer, default=0, nullable=False)
  guessed_2_reward_item_name = Column(String, ForeignKey("dt_items.name", ondelete="SET NULL"), nullable=True)
  guessed_2_item_reward_amount = Column(Integer, default=0, nullable=False)
  guessed_1_reward_item_name = Column(String, ForeignKey("dt_items.name", ondelete="SET NULL"), nullable=True)
  guessed_1_item_reward_amount = Column(Integer, default=0, nullable=False)

  # guessed_4_reward_item = relationship("DTItem", uselist=False, primaryjoin="DTEventItemLottery.guessed_4_reward_item_name==DTItem.name")
  # guessed_3_reward_item = relationship("DTItem", uselist=False, primaryjoin="DTEventItemLottery.guessed_3_reward_item_name==DTItem.name")
  # guessed_2_reward_item = relationship("DTItem", uselist=False, primaryjoin="DTEventItemLottery.guessed_2_reward_item_name==DTItem.name")
  # guessed_1_reward_item = relationship("DTItem", uselist=False, primaryjoin="DTEventItemLottery.guessed_1_reward_item_name==DTItem.name")

  guild = relationship("DiscordGuild", uselist=False, back_populates="lotteries")
  # guesses = relationship("DTEventItemLotteryGuess", uselist=True, primaryjoin="and_(foreign(DTEventItemLottery.guild_id) == DTEventItemLotteryGuess.guild_id, foreign(DTEventItemLottery.event_id) == DTEventItemLotteryGuess.event_id)", viewonly=True)
  event_specification = relationship("EventSpecification", uselist=False)

  async def get_lotery_channel(self, bot: BaseAutoshardedBot) -> Optional[Union[disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable]]:
    if self.lotery_channel_id is None: return None
    guild = await self.guild.to_object(bot)
    if guild is None: return None
    channel = await object_getters.get_or_fetch_channel(guild, int(self.announce_channel_id))
    if not isinstance(channel, (disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable)): return None
    return channel

  async def get_lotery_message(self, bot: BaseAutoshardedBot) -> Optional[disnake.Message]:
    if self.lotery_message_id is None: return None
    channel = await self.get_lotery_channel(bot)
    lotery_message = await object_getters.get_or_fetch_message(bot, channel, int(self.lotery_message_id))
    return lotery_message

  async def get_author(self, bot: BaseAutoshardedBot) -> Optional[disnake.Member]:
    guild = await self.guild.to_object(bot)
    if guild is None: return None
    return await object_getters.get_or_fetch_member(guild, int(self.author_id))

  async def repeat(self):
    next_year, next_week = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))
    event_specification = await event_participation_repo.get_or_create_event_specification(next_year, next_week)
    new_item = DTEventItemLottery(author_id=self.author_id, guild_id=self.guild_id, lottery_channel_id=self.lotery_channel_id, event_id=event_specification.event_id,
                                  guessed_1_reward_item_name=self.guessed_1_reward_item_name, guessed_1_item_reward_amount=self.guessed_1_item_reward_amount,
                                  guessed_2_reward_item_name=self.guessed_2_reward_item_name, guessed_2_item_reward_amount=self.guessed_2_item_reward_amount,
                                  guessed_3_reward_item_name=self.guessed_3_reward_item_name, guessed_3_item_reward_amount=self.guessed_3_item_reward_amount,
                                  guessed_4_reward_item_name=self.guessed_4_reward_item_name, guessed_4_item_reward_amount=self.guessed_4_item_reward_amount)
    database.session.add(new_item)
    database.session.delete(self)
    await database.run_commit()
    return new_item