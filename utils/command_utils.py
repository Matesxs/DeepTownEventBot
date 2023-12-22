from disnake.permissions import Permissions
from disnake.app_commands import Option, Localized
from disnake.ext.commands import InvokableSlashCommand
from disnake.ext import commands
import asyncio
from typing import Union, Optional, List, Dict, Any, Callable
import os

from config import config

# https://github.com/Toaster192/rubbergod/blob/master/utils.py
def get_command_signature(cmd_src: Union[commands.Context, commands.Command]):
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
