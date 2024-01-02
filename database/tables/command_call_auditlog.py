from sqlalchemy import Column, String, Enum, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship

import database
from utils.command_utils import CommandTypes

class CommandCallAuditlog(database.base):
  __tablename__ = "command_call_auditlogs"

  id = Column(database.BigIntegerType, primary_key=True, autoincrement=True)

  created_at = Column(DateTime, nullable=False, index=True)

  author_id = Column(ForeignKey("discord_users.id", ondelete="CASCADE"), nullable=False, index=True)
  guild_id = Column(ForeignKey("discord_guilds.id", ondelete="CASCADE"), nullable=True, index=True)

  command = Column(String, nullable=False, index=True)
  command_type = Column(Enum(CommandTypes), nullable=False, index=True)
  cog = Column(String, nullable=True, index=True)

  args = Column(String, nullable=False)

  failed = Column(Boolean, nullable=False, index=True)

  author = relationship("DiscordUser", uselist=False, back_populates="command_calls")
  guild = relationship("DiscordGuild", uselist=False, back_populates="command_calls")

  @classmethod
  async def create_from_context(cls, data: dict, failed: bool):
    item = cls(created_at=data["created_at"],
               author_id=str(data["author"].id),
               guild_id=str(data["guild"].id) if data["guild"] is not None else None,
               command=data["command"],
               command_type=data["command_type"],
               cog=data["cog"],
               args=data["args"],
               failed=failed)

    await database.add_item(item)

    return item
