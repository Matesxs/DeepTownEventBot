import datetime
import disnake
from disnake.permissions import Permissions
from disnake.app_commands import Option, Localized
from disnake.ext.commands import InvokableSlashCommand, InvokableMessageCommand
from disnake.ext import commands
import asyncio
from typing import Union, Optional, List, Dict, Any, Callable
import os
import enum

from config import config

# https://github.com/Toaster192/rubbergod/blob/master/utils.py
def get_text_command_signature(cmd_src: Union[commands.Context, commands.Command]):
  cmd = cmd_src.command if isinstance(cmd_src, commands.Context) else cmd_src
  cmd_string = f"{cmd} {cmd.signature}".rstrip(" ")
  return f"{cmd_string}"

def get_cogs_in_folder(folder: str="extensions"):
  return [cog[:-3].lower() for cog in os.listdir(folder) if str(cog).endswith(".py") and "__init__" not in str(cog)]

def master_only_slash_command(
    *,
    name: Union[Optional[str], Localized[Optional[str]]] = None,
    description: Union[Optional[str], Localized[Optional[str]]] = None,
    default_member_permissions: Optional[Union[Permissions, int]] = None,
    nsfw: Optional[bool] = None,
    options: Optional[List[Option]] = None,
    connectors: Optional[Dict[str, str]] = None,
    auto_sync: Optional[bool] = None,
    extras: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Callable:
  def decorator(func) -> InvokableSlashCommand:
    if not asyncio.iscoroutinefunction(func):
      raise TypeError(f"<{func.__qualname__}> must be a coroutine function")
    if hasattr(func, "__command_flag__"):
      raise TypeError("Callback is already a command.")
    if config.base.master_discord_guild_ids and not all(isinstance(guild_id, int) for guild_id in config.base.master_discord_guild_ids):
      raise ValueError("guild_ids must be a sequence of int.")
    return InvokableSlashCommand(
      func,
      name=name,
      description=(description + " (Master Server only)") if description is not None else "(Master Server only)",
      options=options,
      dm_permission=False,
      default_member_permissions=default_member_permissions,
      nsfw=nsfw,
      guild_ids=config.base.master_discord_guild_ids,
      connectors=connectors,
      auto_sync=auto_sync,
      extras=extras,
      **kwargs,
    )

  return decorator

def master_only_message_command(
*,
    name: Union[Optional[str], Localized[Optional[str]]] = None,
    dm_permission: Optional[bool] = None,
    default_member_permissions: Optional[Union[Permissions, int]] = None,
    nsfw: Optional[bool] = None,
    auto_sync: Optional[bool] = None,
    extras: Optional[Dict[str, Any]] = None,
    **kwargs,
) -> Callable:
  def decorator(func) -> InvokableMessageCommand:
    if not asyncio.iscoroutinefunction(func):
      raise TypeError(f"<{func.__qualname__}> must be a coroutine function")
    if hasattr(func, "__command_flag__"):
      raise TypeError("Callback is already a command.")
    if config.base.master_discord_guild_ids and not all(isinstance(guild_id, int) for guild_id in config.base.master_discord_guild_ids):
      raise ValueError("guild_ids must be a sequence of int.")
    return InvokableMessageCommand(
      func,
      name=name,
      dm_permission=dm_permission,
      default_member_permissions=default_member_permissions,
      nsfw=nsfw,
      guild_ids=config.base.master_discord_guild_ids,
      auto_sync=auto_sync,
      extras=extras,
      **kwargs,
    )

  return decorator

class CommandTypes(enum.Enum):
  SLASH_COMMAND = enum.auto()
  SLASH_COMMAND_GROUP = enum.auto()
  USER_COMMAND = enum.auto()
  MESSAGE_COMMAND = enum.auto()
  TEXT_COMMAND = enum.auto()
  UNKNOWN_COMMAND = enum.auto()

def get_command_type(command: commands.InvokableApplicationCommand):
  if isinstance(command, commands.InvokableUserCommand):
    return CommandTypes.USER_COMMAND
  elif isinstance(command, commands.InvokableMessageCommand):
    return CommandTypes.MESSAGE_COMMAND
  elif isinstance(command, commands.InvokableSlashCommand) or isinstance(command, commands.slash_core.SubCommand):
    return CommandTypes.SLASH_COMMAND
  elif isinstance(command, commands.SubCommandGroup):
    return CommandTypes.SLASH_COMMAND_GROUP
  else:
    return CommandTypes.UNKNOWN_COMMAND


async def parse_context(ctx: Union[disnake.ApplicationCommandInteraction, commands.Context]):
  if isinstance(ctx, disnake.ApplicationCommandInteraction):
    args = " ".join(f"{key}={item}" for key, item in ctx.filled_options.items())
    commad_type = get_command_type(ctx.application_command)

    return {
      "args": args,
      "cog": ctx.application_command.cog_name,
      "command_type": commad_type,
      "command": f"{ctx.application_command.qualified_name}",
      "url": getattr(ctx.channel, "jump_url", None),
      "author": ctx.author,
      "guild": ctx.guild,
      "created_at": ctx.created_at.replace(tzinfo=None)
    }
  elif isinstance(ctx, commands.Context):
    return {
      "args": ctx.message.content,
      "cog": ctx.cog.qualified_name if ctx.cog is not None else None,
      "command_type": CommandTypes.TEXT_COMMAND,
      "command": f"{ctx.command.qualified_name}",
      "url": getattr(ctx.message, "jump_url", None),
      "author": ctx.author,
      "guild": ctx.guild,
      "created_at": datetime.datetime.now(datetime.UTC)
    }
  else:
    raise NotImplementedError
