import disnake
from typing import Optional, Union, List
from sqlalchemy import select, delete, text, func

from database import run_commit_in_thread, run_query_in_thread
from database.tables.discord_objects import DiscordGuild, DiscordUser, DiscordMember

async def get_discord_guild(session, guild_id: int) -> Optional[DiscordGuild]:
  result = await run_query_in_thread(session, select(DiscordGuild).filter(DiscordGuild.id == str(guild_id)))
  return result.scalar_one_or_none()

async def get_or_create_discord_guild(session, guild: disnake.Guild, commit: bool=True) -> DiscordGuild:
  guild_it = await get_discord_guild(session, guild.id)
  if guild_it is None:
    guild_it = DiscordGuild.from_guild(guild)
    session.add(guild_it)
    await run_commit_in_thread(session)
  else:
    guild_it.update(guild)

    if commit:
      await run_commit_in_thread(session)
  return guild_it

async def remove_discord_guild(session, guild_id: int):
  await run_query_in_thread(session, delete(DiscordGuild).filter(DiscordGuild.id == str(guild_id)), commit=True)

async def discord_guild_cleanup(session, current_guild_ids: List[str]):
  await run_query_in_thread(session, delete(DiscordGuild).filter(DiscordGuild.id.notin_(current_guild_ids)), commit=True)

async def better_message_links_enabled(session, guild_id: int) -> bool:
  result = (await run_query_in_thread(session, select(DiscordGuild.enable_better_message_links).filter(DiscordGuild.id == str(guild_id)))).scalar_one_or_none()
  return result if result is not None else False

async def get_discord_user(session, user_id: int) -> Optional[DiscordUser]:
  result = await run_query_in_thread(session, select(DiscordUser).filter(DiscordUser.id == str(user_id)))
  return result.scalar_one_or_none()

async def get_or_create_discord_user(session, user: Union[disnake.Member, disnake.User], comit: bool=True) -> DiscordUser:
  item = await get_discord_user(session, user.id)
  if item is None:
    item = DiscordUser.from_user(user)
    session.add(item)
    await run_commit_in_thread(session)
  else:
    item.update(user)

    if comit:
      await run_commit_in_thread(session)

  return item

async def remove_discord_user(session, user_id: int):
  await run_query_in_thread(session, delete(DiscordUser).filter(DiscordUser.id == str(user_id)), commit=True)

async def discord_user_cleanup(session):
  await run_query_in_thread(session, text(f"""
  DELETE
  FROM discord_users
  WHERE (discord_users.id NOT IN (SELECT DISTINCT discord_members.user_id
                                  FROM discord_members));
  """), commit=True)

async def get_discord_member(session, guild_id: int, user_id: int) -> Optional[DiscordMember]:
  result = await run_query_in_thread(session, select(DiscordMember).filter(DiscordMember.guild_id == str(guild_id), DiscordMember.user_id == str(user_id)))
  return result.scalar_one_or_none()

async def get_or_create_discord_member(session, member: disnake.Member, comit: bool=True) -> DiscordMember:
  user_item = await get_or_create_discord_user(session, member, comit=True)
  item = await get_discord_member(session, member.guild.id, member.id)

  if item is None:
    await get_or_create_discord_guild(session, member.guild, commit=False)

    item = DiscordMember.from_member(member)
    session.add(item)
    await run_commit_in_thread(session)
  else:
    user_item.update(member)
    item.update(member)

    if comit:
      await run_commit_in_thread(session)

  return item

async def remove_discord_member(session, guild_id: int, user_id: int):
  await run_query_in_thread(session, delete(DiscordMember).filter(DiscordMember.guild_id == str(guild_id), DiscordMember.user_id == str(user_id)), commit=True)

  result = await run_query_in_thread(session, select(func.count(DiscordMember.guild_id)).filter(DiscordMember.user_id == str(user_id), DiscordMember.guild_id != str(guild_id)))
  if result.scalar_one() == 0:
    await remove_discord_user(session, user_id)

async def discord_member_cleanup(session, guild_id: int, current_user_ids: List[str]):
  await run_query_in_thread(session, delete(DiscordMember).filter(DiscordMember.guild_id == str(guild_id), DiscordMember.user_id.notin_(current_user_ids)), commit=True)
