import re
from typing import Optional, Tuple

from database import dt_user_repo, dt_guild_repo, dt_items_repo
from utils import string_manipulation

id_in_identifier_regex = re.compile(r"([A-Z]*) .*\((\d*)\).*")

async def autocomplete_identifier_user(_, string: str):
  if string is None or not string:
    return [f"USER {string_manipulation.truncate_string(user.username, 40)} ({user.id})" for user in (await dt_user_repo.get_all_users(limit=20))]
  return [f"USER {string_manipulation.truncate_string(user.username, 40)} ({user.id})" for user in (await dt_user_repo.get_all_users(search=string, limit=20))]

async def autocomplete_identifier_guild(_, string: str):
  if string is None or not string:
    return [f"GUILD {string_manipulation.truncate_string(guild.name, 40)} ({guild.id})" for guild in (await dt_guild_repo.search_guilds(limit=20))]
  return [f"GUILD {string_manipulation.truncate_string(guild.name, 40)} ({guild.id})" for guild in (await dt_guild_repo.search_guilds(search=string, limit=20))]

async def autocomplete_identifier_guild_and_user(_, string: str):
  if string is None or not string:
    result = [f"USER {string_manipulation.truncate_string(user.username, 40)} ({user.id})" for user in (await dt_user_repo.get_all_users(limit=20))]
    rest = 20 - len(result)
    if rest > 0:
      result.extend([f"GUILD {string_manipulation.truncate_string(guild.name, 40)} ({guild.id})" for guild in (await dt_guild_repo.search_guilds(limit=rest))])
    return result

  result = [f"USER {string_manipulation.truncate_string(user.username, 40)} ({user.id})" for user in (await dt_user_repo.get_all_users(search=string, limit=20))]
  rest = 20 - len(result)
  if rest > 0:
    result.extend([f"GUILD {string_manipulation.truncate_string(guild.name, 40)} ({guild.id})" for guild in (await dt_guild_repo.search_guilds(search=string, limit=20))])
  return result

async def autocomplete_item(_, string: str):
  return await dt_items_repo.search_items(string, limit=20)

async def autocomplete_craftable_item(_, string: str):
  return await dt_items_repo.search_craftable_items(string, limit=20)

def identifier_to_specifier(identifier: str) -> Optional[Tuple[str, int]]:
  specifier = id_in_identifier_regex.findall(identifier)
  if len(specifier) != 1 or len(specifier[0]) != 2 or not str(specifier[0][1]).isnumeric():
    return None
  return str(specifier[0][0]), int(specifier[0][1])
