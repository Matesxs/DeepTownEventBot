import disnake
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from typing import Optional, Union

import database
from utils import object_getters
from features.base_bot import BaseAutoshardedBot

class AutomaticLotteryGuessesWhitelist(database.base):
  __tablename__ = "automatic_lottery_guesses_whitelist"

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
  