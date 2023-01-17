import math
from typing import List, Tuple, Optional, Iterator
import disnake

from database import session, guilds_repo
from database.tables.questions_and_answers import QuestionAndAnswer, QuestionAndAnswerWhitelist

def is_on_whitelist(guild_id: int, channel_id: int) -> bool:
  return session.query(QuestionAndAnswerWhitelist.channel_id).filter(QuestionAndAnswerWhitelist.guild_id == str(guild_id), QuestionAndAnswerWhitelist.channel_id == str(channel_id)).one_or_none() is not None

def add_to_whitelist(guild: disnake.Guild, channel_id: int) -> bool:
  if is_on_whitelist(guild.id, channel_id):
    return False

  guilds_repo.get_or_create_discord_guild(guild)

  item = QuestionAndAnswerWhitelist(guild_id=str(guild.id), channel_id=str(channel_id))
  session.add(item)
  session.commit()
  return True

def get_guild_whitelisted_channel_ids(guild_id: int) -> List[int]:
  data = session.query(QuestionAndAnswerWhitelist.channel_id).filter(QuestionAndAnswerWhitelist.guild_id == str(guild_id)).all()
  return [int(d[0]) for d in data]

def remove_from_whitelist(guild_id: int, channel_id: int) -> bool:
  result = session.query(QuestionAndAnswerWhitelist).filter(QuestionAndAnswerWhitelist.guild_id == str(guild_id), QuestionAndAnswerWhitelist.channel_id == str(channel_id)).delete()
  return result > 0

def get_question_and_answer(qa_id: int) -> Optional[QuestionAndAnswer]:
  return session.query(QuestionAndAnswer).filter(QuestionAndAnswer.id == qa_id).one_or_none()

def find_question(question: str) -> Optional[QuestionAndAnswer]:
  return session.query(QuestionAndAnswer).filter(QuestionAndAnswer.question == question).one_or_none()

def create_question_and_answer(question: str, answer: str) -> Optional[QuestionAndAnswer]:
  if find_question(question) is not None:
    return None

  item = QuestionAndAnswer(question=question, answer=answer)
  session.add(item)
  session.commit()
  return item

def all_questions_iterator() -> Iterator[Tuple[int, str]]:
  number_of_questions = session.query(QuestionAndAnswer.id).count()
  number_of_batches = math.ceil(number_of_questions / 10)

  for batch_index in range(number_of_batches):
    data = session.query(QuestionAndAnswer.id, QuestionAndAnswer.question).offset(batch_index * 10).limit(10)
    for d in data:
      yield d[0], d[1]

def get_answer_by_id(ans_id: int) -> Optional[str]:
  data = session.query(QuestionAndAnswer.answer).filter(QuestionAndAnswer.id == ans_id).one_or_none()
  return str(data[0]) if data is not None else None

def get_all() -> List[QuestionAndAnswer]:
  return session.query(QuestionAndAnswer).all()

def get_all_ids() -> List[int]:
  data = session.query(QuestionAndAnswer.id).all()
  return [d[0] for d in data]

def remove_question(id: int):
  result = session.query(QuestionAndAnswer).filter(QuestionAndAnswer.id == id).delete()
  session.commit()
  return result > 0
