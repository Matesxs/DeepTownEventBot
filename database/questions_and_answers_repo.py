from typing import List, Tuple, Optional, AsyncIterator
import disnake
from sqlalchemy import select, delete

from database import run_query_in_thread, run_commit_in_thread, discord_objects_repo
from database.tables.questions_and_answers import QuestionAndAnswer, QuestionAndAnswerWhitelist

async def is_on_whitelist(session, guild_id: int, channel_id: int) -> bool:
  result = await run_query_in_thread(session, select(QuestionAndAnswerWhitelist.channel_id).filter(QuestionAndAnswerWhitelist.guild_id == str(guild_id), QuestionAndAnswerWhitelist.channel_id == str(channel_id)))
  return result.scalar_one_or_none() is not None

async def add_to_whitelist(session, guild: disnake.Guild, channel_id: int) -> bool:
  if await is_on_whitelist(session, guild.id, channel_id):
    return False

  await discord_objects_repo.get_or_create_discord_guild(session, guild)

  item = QuestionAndAnswerWhitelist(guild_id=str(guild.id), channel_id=str(channel_id))
  session.add(item)
  await run_commit_in_thread(session)

  return True

async def remove_from_whitelist(session, guild_id: int, channel_id: int) -> bool:
  result = await run_query_in_thread(session, delete(QuestionAndAnswerWhitelist).filter(QuestionAndAnswerWhitelist.guild_id == str(guild_id), QuestionAndAnswerWhitelist.channel_id == str(channel_id)), commit=True)
  return result.rowcount > 0

async def get_whitelist_channels(session, guild_id: int) -> List[QuestionAndAnswerWhitelist]:
  result = await run_query_in_thread(session, select(QuestionAndAnswerWhitelist).filter(QuestionAndAnswerWhitelist.guild_id == str(guild_id)))
  return result.scalars().all()

async def get_question_and_answer(session, qa_id: int) -> Optional[QuestionAndAnswer]:
  result = await run_query_in_thread(session, select(QuestionAndAnswer).filter(QuestionAndAnswer.id == qa_id))
  return result.scalar_one_or_none()

async def find_question(session, question: str) -> Optional[QuestionAndAnswer]:
  result = await run_query_in_thread(session, select(QuestionAndAnswer).filter(QuestionAndAnswer.question == question))
  return result.scalar_one_or_none()

async def create_question_and_answer(session, question: str, answer: str) -> Optional[QuestionAndAnswer]:
  if (await find_question(session, question)) is not None:
    return None

  item = QuestionAndAnswer(question=question, answer=answer)
  session.add(item)
  await run_commit_in_thread(session)

  return item

async def all_questions_iterator(session) -> AsyncIterator[Tuple[int, str]]:
  result = await run_query_in_thread(session, select(QuestionAndAnswer.id, QuestionAndAnswer.question).execution_options(yield_per=50))
  for partition in result.partitions():
    for row in partition:
      yield row[0], row[1]

async def get_answer_by_id(session, ans_id: int) -> Optional[str]:
  result = await run_query_in_thread(session, select(QuestionAndAnswer.answer).filter(QuestionAndAnswer.id == ans_id))
  return result.scalar_one_or_none()

async def get_all(session) -> List[QuestionAndAnswer]:
  result = await run_query_in_thread(session, select(QuestionAndAnswer))
  return result.scalars().all()

async def get_all_ids(session) -> List[int]:
  result = await run_query_in_thread(session, select(QuestionAndAnswer.id))
  return result.scalars().all()

async def remove_question(session, id_: int) -> bool:
  result = await run_query_in_thread(session, delete(QuestionAndAnswer).filter(QuestionAndAnswer.id == id_), commit=True)
  return result.rowcount > 0
