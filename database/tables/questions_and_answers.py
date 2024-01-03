import disnake
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from typing import Optional, Union

import database
from utils import object_getters
from features.base_bot import BaseAutoshardedBot

class QuestionAndAnswerWhitelist(database.base):
  __tablename__ = "questions_and_answers_whitelist"

  guild_id = Column(String, ForeignKey("discord_guilds.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
  channel_id = Column(String, primary_key=True)

  guild = relationship("DiscordGuild", uselist=False)

  async def get_channel(self, bot: BaseAutoshardedBot) -> Optional[Union[disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable]]:
    if self.channel_id is None: return None
    guild = await self.guild.to_object(bot)
    if guild is None: return None
    channel = await object_getters.get_or_fetch_channel(guild, int(self.channel_id))
    if not isinstance(channel, (disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable)): return None
    return channel

class QuestionAndAnswer(database.base):
  __tablename__ = "questions_and_answers"

  id = Column(database.BigIntegerType, primary_key=True, unique=True, index=True, autoincrement=True)

  question = Column(String, nullable=False, index=True, unique=True)
  answer = Column(String, nullable=False)
