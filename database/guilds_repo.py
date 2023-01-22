import disnake
from typing import Optional
from sqlalchemy import select, delete

from database import run_commit, run_query, session
from database.tables.guilds import DiscordGuild

async def get_discord_guild(guild_id: int) -> Optional[DiscordGuild]:
  result = await run_query(select(DiscordGuild).filter(DiscordGuild.id == str(guild_id)))
  return result.scalar_one_or_none()

async def get_or_create_discord_guild(guild: disnake.Guild, commit: bool=True) -> DiscordGuild:
  guild_it = await get_discord_guild(guild.id)
  if guild_it is None:
    guild_it = DiscordGuild.from_guild(guild)
    session.add(guild_it)

    if commit:
      await run_commit()
  return guild_it

async def remove_discord_guild(guild_id: int):
  await run_query(delete(DiscordGuild).filter(DiscordGuild.id == str(guild_id)))
  await run_commit()
