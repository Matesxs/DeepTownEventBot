from typing import List, Tuple, Optional, AsyncIterator
import disnake
from sqlalchemy import select, delete

from database import run_query, run_commit, add_item, discord_objects_repo
from database.tables.questions_and_answers import QuestionAndAnswer, QuestionAndAnswerWhitelist

async def is_on_whitelist(guild_id: int, channel_id: int) -> bool:
  result = await run_query(select(QuestionAndAnswerWhitelist.channel_id).filter(QuestionAndAnswerWhitelist.guild_id == str(guild_id), QuestionAndAnswerWhitelist.channel_id == str(channel_id)))
  return result.scalar_one_or_none() is not None

async def add_to_whitelist(guild: disnake.Guild, channel_id: int) -> bool:
  if await is_on_whitelist(guild.id, channel_id):
    return False

  await discord_objects_repo.get_or_create_discord_guild(guild)

  item = QuestionAndAnswerWhitelist(guild_id=str(guild.id), channel_id=str(channel_id))
  await add_item(item)

  return True

async def remove_from_whitelist(guild_id: int, channel_id: int) -> bool:
  result = await run_query(delete(QuestionAndAnswerWhitelist).filter(QuestionAndAnswerWhitelist.guild_id == str(guild_id), QuestionAndAnswerWhitelist.channel_id == str(channel_id)))
  await run_commit()
  return result.rowcount > 0

async def get_question_and_answer(qa_id: int) -> Optional[QuestionAndAnswer]:
  result = await run_query(select(QuestionAndAnswer).filter(QuestionAndAnswer.id == qa_id))
  return result.scalar_one_or_none()

async def find_question(question: str) -> Optional[QuestionAndAnswer]:
  result = await run_query(select(QuestionAndAnswer).filter(QuestionAndAnswer.question == question))
  return result.scalar_one_or_none()

async def create_question_and_answer(question: str, answer: str) -> Optional[QuestionAndAnswer]:
  if (await find_question(question)) is not None:
    return None

  item = QuestionAndAnswer(question=question, answer=answer)
  await add_item(item)

  await run_commit()
  return item

async def all_questions_iterator() -> AsyncIterator[Tuple[int, str]]:
  result = await run_query(select(QuestionAndAnswer.id, QuestionAndAnswer.question).execution_options(yield_per=50))
  for partition in result.partitions():
    for row in partition:
      yield row[0], row[1]

async def get_answer_by_id(ans_id: int) -> Optional[str]:
  result = await run_query(select(QuestionAndAnswer.answer).filter(QuestionAndAnswer.id == ans_id))
  return result.scalar_one_or_none()

async def get_all() -> List[QuestionAndAnswer]:
  result = await run_query(select(QuestionAndAnswer))
  return result.scalars().all()

async def get_all_ids() -> List[int]:
  result = await run_query(select(QuestionAndAnswer.id))
  return result.scalars().all()

async def remove_question(id: int) -> bool:
  result = await run_query(delete(QuestionAndAnswer).filter(QuestionAndAnswer.id == id))
  await run_commit()
  return result.rowcount > 0
