import disnake
from typing import Optional, Union, List
from sqlalchemy import select, delete

from database import run_commit, run_query, session
from database.tables.discord_objects import DiscordGuild, DiscordUser, DiscordMember

async def get_discord_guild(guild_id: int) -> Optional[DiscordGuild]:
  result = await run_query(select(DiscordGuild).filter(DiscordGuild.id == str(guild_id)))
  return result.scalar_one_or_none()

async def get_or_create_discord_guild(guild: disnake.Guild, commit: bool=True) -> DiscordGuild:
  guild_it = await get_discord_guild(guild.id)
  if guild_it is None:
    guild_it = DiscordGuild.from_guild(guild)
    session.add(guild_it)
  else:
    guild_it.update(guild)

  if commit:
    await run_commit()
  return guild_it

async def remove_discord_guild(guild_id: int):
  await run_query(delete(DiscordGuild).filter(DiscordGuild.id == str(guild_id)))
  await run_commit()

async def discord_guild_cleanup(current_guild_ids: List[str]):
  await run_query(delete(DiscordGuild).filter(DiscordGuild.id.notin_(current_guild_ids)), commit=True)

async def get_discord_user(user_id: int) -> Optional[DiscordUser]:
  result = await run_query(select(DiscordUser).filter(DiscordUser.id == str(user_id)))
  return result.scalar_one_or_none()

async def get_or_create_discord_user(user: Union[disnake.Member, disnake.User], comit: bool=True) -> DiscordUser:
  item = await get_discord_user(user.id)
  if item is None:
    item = DiscordUser.from_user(user)
    session.add(item)
  else:
    item.update(user)

  if comit:
    await run_commit()

  return item

async def remove_discord_user(user_id: int):
  await run_query(delete(DiscordUser).filter(DiscordUser.id == str(user_id)))
  await run_commit()

async def discord_user_cleanup():
  await run_query(f"""
  DELETE
  FROM discord_users
  WHERE (discord_users.id NOT IN (SELECT DISTINCT discord_members.user_id
                                  FROM discord_members));
  """, commit=True)

async def get_discord_member(guild_id: int, user_id: int) -> Optional[DiscordMember]:
  result = await run_query(select(DiscordMember).filter(DiscordMember.guild_id == str(guild_id), DiscordMember.user_id == str(user_id)))
  return result.scalar_one_or_none()

async def get_or_create_discord_member(member: disnake.Member, comit: bool=True) -> DiscordMember:
  item = await get_discord_member(member.guild.id, member.id)
  if item is None:
    await get_or_create_discord_guild(member.guild, commit=False)
    await get_or_create_discord_user(member, comit=True)

    item = DiscordMember.from_member(member)
    session.add(item)
  else:
    item.update(member)

  if comit:
    await run_commit()

  return item

async def remove_discord_member(guild_id: int, user_id: int):
  await run_query(delete(DiscordMember).filter(DiscordMember.guild_id == str(guild_id), DiscordMember.user_id == str(user_id)))
  await run_commit()

async def discord_member_cleanup(guild_id: int, current_user_ids: List[str]):
  await run_query(delete(DiscordMember).filter(DiscordMember.guild_id == str(guild_id), DiscordMember.user_id.notin_(current_user_ids)), commit=True)
