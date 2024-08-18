import disnake
from sqlalchemy import select, delete
from typing import List

from database import run_query_in_thread, run_commit_in_thread, discord_objects_repo
from database.tables.automatic_lottery_guesses_whitelist import AutomaticLotteryGuessesWhitelist

async def is_on_whitelist(session, guild_id: int, channel_id: int) -> bool:
  result = await run_query_in_thread(session, select(AutomaticLotteryGuessesWhitelist.channel_id).filter(AutomaticLotteryGuessesWhitelist.guild_id == str(guild_id), AutomaticLotteryGuessesWhitelist.channel_id == str(channel_id)))
  return result.scalar_one_or_none() is not None

async def add_to_whitelist(session, guild: disnake.Guild, channel_id: int) -> bool:
  if await is_on_whitelist(session, guild.id, channel_id):
    return False

  await discord_objects_repo.get_or_create_discord_guild(session, guild)

  item = AutomaticLotteryGuessesWhitelist(guild_id=str(guild.id), channel_id=str(channel_id))
  session.add(item)
  await run_commit_in_thread(session)

  return True

async def remove_from_whitelist(session, guild_id: int, channel_id: int) -> bool:
  result = await run_query_in_thread(session, delete(AutomaticLotteryGuessesWhitelist).filter(AutomaticLotteryGuessesWhitelist.guild_id == str(guild_id), AutomaticLotteryGuessesWhitelist.channel_id == str(channel_id)), commit=True)
  return result.rowcount > 0

async def get_whitelist_channels(session, guild_id: int) -> List[AutomaticLotteryGuessesWhitelist]:
  result = await run_query_in_thread(session, select(AutomaticLotteryGuessesWhitelist).filter(AutomaticLotteryGuessesWhitelist.guild_id == str(guild_id)))
  return result.scalars().all()
