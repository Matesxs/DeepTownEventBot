import disnake
from typing import Optional

from database import session
from database.tables.guilds import DiscordGuild

def get_discord_guild(guild_id: int) -> Optional[DiscordGuild]:
  return session.query(DiscordGuild).filter(DiscordGuild.id == str(guild_id)).one_or_none()

def get_or_create_discord_guild(guild: disnake.Guild, commit: bool=True) -> DiscordGuild:
  guild_it = get_discord_guild(guild.id)
  if guild_it is None:
    guild_it = DiscordGuild.from_guild(guild)
    session.add(guild_it)
    if commit:
      session.commit()
  return guild_it

def remove_discord_guild(guild_id: int):
  session.query(DiscordGuild).filter(DiscordGuild.id == str(guild_id)).delete()
  session.commit()
