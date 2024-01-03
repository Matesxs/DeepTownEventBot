import disnake
from sqlalchemy import select, delete
from typing import List

from database import run_query, add_item, discord_objects_repo
from database.tables.automatic_lottery_guesses_whitelist import AutomaticLotteryGuessesWhitelist

async def is_on_whitelist(guild_id: int, channel_id: int) -> bool:
  result = await run_query(select(AutomaticLotteryGuessesWhitelist.channel_id).filter(AutomaticLotteryGuessesWhitelist.guild_id == str(guild_id), AutomaticLotteryGuessesWhitelist.channel_id == str(channel_id)))
  return result.scalar_one_or_none() is not None

async def add_to_whitelist(guild: disnake.Guild, channel_id: int) -> bool:
  if await is_on_whitelist(guild.id, channel_id):
    return False

  await discord_objects_repo.get_or_create_discord_guild(guild)

  item = AutomaticLotteryGuessesWhitelist(guild_id=str(guild.id), channel_id=str(channel_id))
  await add_item(item)

  return True

async def remove_from_whitelist(guild_id: int, channel_id: int) -> bool:
  result = await run_query(delete(AutomaticLotteryGuessesWhitelist).filter(AutomaticLotteryGuessesWhitelist.guild_id == str(guild_id), AutomaticLotteryGuessesWhitelist.channel_id == str(channel_id)), commit=True)
  return result.rowcount > 0

async def get_whitelist_channels(guild_id: int) -> List[AutomaticLotteryGuessesWhitelist]:
  result = await run_query(select(AutomaticLotteryGuessesWhitelist).filter(AutomaticLotteryGuessesWhitelist.guild_id == str(guild_id)))
  return result.scalars().all()
