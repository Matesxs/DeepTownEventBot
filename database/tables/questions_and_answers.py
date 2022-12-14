from sqlalchemy import Column, String, ForeignKey

from database import database, BigIntegerType

class QuestionAndAnswerWhitelist(database.base):
  __tablename__ = "questions_and_answers_whitelist"

  guild_id = Column(String, ForeignKey("guilds.id", ondelete="CASCADE"), primary_key=True)
  channel_id = Column(String, primary_key=True)

class QuestionAndAnswer(database.base):
  __tablename__ = "questions_and_answers"

  id = Column(BigIntegerType, primary_key=True, unique=True, index=True, autoincrement=True)

  question = Column(String, nullable=False, index=True, unique=True)
  answer = Column(String, nullable=False)
