import re
import datetime
from typing import Optional, Tuple
from sqlalchemy import exc

from database import dt_user_repo, dt_guild_repo, dt_items_repo, event_participation_repo, tracking_settings_repo, questions_and_answers_repo, session_maker
from utils import string_manipulation, dt_helpers
from utils.logger import setup_custom_logger

id_in_identifier_regex = re.compile(r"([A-Z]*) .*\((\d*)\).*")
logger = setup_custom_logger(__name__)

async def autocomplete_identifier_user(_, string: Optional[str]):
  user_strings = []

  with session_maker() as session:
    if string is None or not string:
      all_users = await dt_user_repo.get_all_users(session, limit=25)
      for user in all_users:
        prefix = f"USER ({user.id}) "
        prefix_len = len(prefix)
        user_strings.append(prefix + string_manipulation.truncate_string(user.username, 25 - prefix_len))
      return user_strings

  all_users = await dt_user_repo.get_all_users(session, limit=25, search=string)
  for user in all_users:
    prefix = f"USER ({user.id}) "
    prefix_len = len(prefix)
    user_strings.append(prefix + string_manipulation.truncate_string(user.username, 25 - prefix_len))
  return user_strings

async def autocomplete_identifier_guild(_, string: Optional[str]):
  guild_strings = []

  with session_maker() as session:
    if string is None or not string:
      all_guilds = await dt_guild_repo.search_guilds(session, limit=25)
      for guild in all_guilds:
        prefix = F"GUILD ({guild.id}) "
        prefix_length = len(prefix)
        guild_strings.append(prefix + string_manipulation.truncate_string(guild.name, 25 - prefix_length))
      return guild_strings

    all_guilds = await dt_guild_repo.search_guilds(session, limit=25, search=string)
    for guild in all_guilds:
      prefix = F"GUILD ({guild.id}) "
      prefix_length = len(prefix)
      guild_strings.append(prefix + string_manipulation.truncate_string(guild.name, 25 - prefix_length))
    return guild_strings

async def autocomplete_identifier_guild_and_user(_, string: Optional[str]):
  result = await autocomplete_identifier_user(None, string)
  rest = 25 - len(result)
  if rest > 0:
    guilds = await autocomplete_identifier_guild(None, string)
    for _ in range(min(rest, len(guilds))):
      result.append(guilds.pop())
  return result

async def autocomplete_item(_, string: str):
  with session_maker() as session:
    return await dt_items_repo.search_items(session, string, limit=20)

async def autocomplete_craftable_item(_, string: str):
  with session_maker() as session:
    return await dt_items_repo.search_craftable_items(session, string, limit=20)

def guild_user_identifier_converter(_, identifier: str) -> Optional[Tuple[Optional[str], int]]:
  if identifier.isnumeric():
    return None, int(identifier)

  specifier = id_in_identifier_regex.findall(identifier)
  if len(specifier) != 1 or len(specifier[0]) != 2 or not str(specifier[0][1]).isnumeric(): return None
  return str(specifier[0][0]), int(specifier[0][1])

async def autocomplete_event_identifier(_, string: str):
  with session_maker() as session:
    results = await event_participation_repo.search_event_identificator(session, string, limit=20)
    return [f"{result[0]} {result[1]}" for result in results]

def event_identifier_converter(_, string: str) -> Tuple[int, int]:
  if string is None:
    return dt_helpers.get_event_index(datetime.datetime.now(datetime.UTC).replace(tzinfo=None))

  splits = string.split(" ")
  if len(splits) != 2 or not splits[0].isnumeric() or not splits[1].isnumeric() or \
    int(splits[0]) < 1 or int(splits[1]) < 1:
    return dt_helpers.get_event_index(datetime.datetime.now(datetime.UTC).replace(tzinfo=None))
  return int(splits[0]), int(splits[1])

async def autocomplete_event_year(_, string: str):
  with session_maker() as session:
    return await event_participation_repo.search_event_year(session, string, 20)

async def autocomplete_identifier_tracked_guild(inter, string: str):
  with session_maker() as session:
    if string is None or not string:
      return [f"GUILD {string_manipulation.truncate_string(guild.name, 40)} ({guild.id})" for guild in (await tracking_settings_repo.search_tracked_guilds(session, inter.guild_id, limit=20))]
    return [f"GUILD {string_manipulation.truncate_string(guild.name, 40)} ({guild.id})" for guild in (await tracking_settings_repo.search_tracked_guilds(session, inter.guild_id, search=string, limit=20))]

async def question_and_answer_question_id_autocomplete(_, string: str):
  with session_maker() as session:
    question_ids = await questions_and_answers_repo.get_all_ids(session)

  if string is None or not string:
    return question_ids[:25]
  return [id_ for id_ in question_ids if string.lower() in str(id_)][:25]
