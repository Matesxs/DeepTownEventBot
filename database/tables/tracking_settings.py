import disnake
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from typing import Optional, Union

import database
from features.base_bot import BaseAutoshardedBot
from utils import object_getters

class TrackingSettings(database.base):
  __tablename__ = "tracking_settings"

  guild_id = Column(String, ForeignKey("discord_guilds.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)
  dt_guild_id = Column(database.BigIntegerType, ForeignKey("dt_guilds.id", ondelete="CASCADE", onupdate="CASCADE"), primary_key=True)

  text_announce_channel_id = Column(String, nullable=True)
  csv_announce_channel_id = Column(String, nullable=True)

  guild = relationship("DiscordGuild", uselist=False, back_populates="tracking_settings")
  dt_guild = relationship("DTGuild", uselist=False)

  async def get_text_announce_channel(self, bot: BaseAutoshardedBot) -> Optional[Union[disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable]]:
    if self.text_announce_channel_id is None: return None
    guild = await self.guild.to_object(bot)
    if guild is None: return None
    channel = await object_getters.get_or_fetch_channel(guild, int(self.text_announce_channel_id))
    if not isinstance(channel, (disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable)): return None
    return channel

  async def get_csv_announce_channel(self, bot: BaseAutoshardedBot) -> Optional[Union[disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable]]:
    if self.csv_announce_channel_id is None: return None
    guild = await self.guild.to_object(bot)
    if guild is None: return None
    channel = await object_getters.get_or_fetch_channel(guild, int(self.csv_announce_channel_id))
    if not isinstance(channel, (disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable)): return None
    return channel
