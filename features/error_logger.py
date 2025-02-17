import sys
import datetime
import disnake
from disnake.ext import commands
import traceback
from typing import Dict, Optional

from utils import message_utils, command_utils, string_manipulation
from utils.logger import setup_custom_logger
from config import config, Strings
from features import exceptions

logger = setup_custom_logger(__name__)

class ContextMock:
  """Create event context similar to commands.Context
  This will be used in ignore_errors function"""

  def __init__(self, bot, arg):
    self.channel = getattr(arg, "channel", bot.get_channel(arg.channel_id))
    if hasattr(self.channel, "guild"):
      self.guild = self.channel.guild

    if hasattr(arg, "author"):
      self.author = arg.author
    elif hasattr(arg, "member"):
      self.author = arg.member
    else:
      self.author = bot.user

  async def send(self, *args):
    return await self.channel.send(*args)

def create_embed(command: str, cmd_type: command_utils.CommandTypes, error: Exception, args: str, author: disnake.User, guild: Optional[disnake.Guild | str], jump_url: Optional[str], extra_fields: Dict[str, str] = None):
  embed = disnake.Embed(title=f"Ignoring exception in {command}", color=0xFF0000)
  embed.add_field(name="Error", value=type(error).__name__)

  if cmd_type != command_utils.CommandTypes.UNKNOWN_COMMAND:
    embed.add_field(name="Command type", value=cmd_type.name)

  if args:
    embed.add_field(name="Args", value=string_manipulation.truncate_string(args, 1000))

  embed.add_field(name="Autor", value=str(author))

  if guild is not None:
    embed.add_field(name="Guild", value=getattr(guild, "name", guild))

  if jump_url is not None:
    embed.add_field(name="Link", value=jump_url, inline=False)

  if extra_fields:
    for name, value in extra_fields.items():
      embed.add_field(name=name, value=value)
  return embed

async def common_error_handling(ctx, error):
  if isinstance(error, disnake.Forbidden):
    if error.code == 50013:
      res = await message_utils.generate_error_message(ctx, Strings.error_bot_missing_permission)
      if res is None:
        await message_utils.generate_error_message(ctx.author, Strings.error_bot_missing_permission)
    else:
      res = await message_utils.generate_error_message(ctx, Strings.error_forbiden)
      if res is None:
        await message_utils.generate_error_message(ctx.author, Strings.error_forbiden)
  elif isinstance(error, disnake.HTTPException) and error.code == 50007:
    await message_utils.generate_error_message(ctx, Strings.error_blocked_dms)
  elif isinstance(error, commands.CommandNotFound):
    await message_utils.generate_error_message(ctx, Strings.error_unknown_command)
  elif isinstance(error, commands.CommandOnCooldown):
    await message_utils.generate_error_message(ctx, Strings.error_command_on_cooldown(remaining=round(error.retry_after, 2)))
  elif isinstance(error, exceptions.NotGuildAdministrator):
    await message_utils.generate_error_message(ctx, Strings.error_not_administrator)
  elif isinstance(error, exceptions.NoGuildAdministratorRoleAndNotSet):
    await message_utils.generate_error_message(ctx, Strings.error_not_administrator_and_not_set)
  elif isinstance(error, exceptions.NoGuildAdministratorRole):
    await message_utils.generate_error_message(ctx, Strings.not_administrator_role_set)
  elif isinstance(error, exceptions.NotGuildOwner):
    await message_utils.generate_error_message(ctx, Strings.error_not_guild_owner)
  elif isinstance(error, commands.NotOwner):
    await message_utils.generate_error_message(ctx, Strings.error_not_owner)
  elif isinstance(error, exceptions.NotBotDeveloper):
    await message_utils.generate_error_message(ctx, Strings.error_not_developer)
  elif isinstance(error, commands.MissingPermissions):
    await message_utils.generate_error_message(ctx, Strings.error_missing_permission)
  elif isinstance(error, commands.MissingRole):
    await message_utils.generate_error_message(ctx, Strings.error_missing_role(role=error.missing_role))
  elif isinstance(error, commands.MissingRequiredArgument):
    await message_utils.generate_error_message(ctx, Strings.error_missing_argument(argument=error.param, signature=command_utils.get_text_command_signature(ctx)))
  elif isinstance(error, commands.BadArgument):
    await message_utils.generate_error_message(ctx, Strings.error_bad_argument)
  elif isinstance(error, commands.MaxConcurrencyReached):
    await message_utils.generate_error_message(ctx, Strings.error_max_concurrency_reached)
  elif isinstance(error, commands.NoPrivateMessage):
    await message_utils.generate_error_message(ctx, Strings.error_no_private_message)
  elif isinstance(error, disnake.InteractionTimedOut):
    await message_utils.generate_error_message(ctx, Strings.error_interaction_timeout)
  else:
    return False
  return True

class ErrorLogger:
  def __init__(self, bot):
    self.bot = bot

  async def handle_context_error(self, ctx, error, traceback):
    log_channel = self.bot.get_channel(config.base.log_channel_id)
    if log_channel is None: return

    parsed_context = await command_utils.parse_context(ctx)
    embed = create_embed(parsed_context["command"], parsed_context["command_type"], error, parsed_context["args"][:1000], ctx.author, ctx.guild, parsed_context["url"])

    await log_channel.send(embed=embed)

    output = string_manipulation.split_to_parts(traceback, 1900)
    if log_channel is not None:
      for message in output:
        await log_channel.send(f"```\n{message}\n```")

    try:
      await message_utils.generate_error_message(ctx, Strings.error_unknown_error)
    except:
      pass

  async def default_error_handling(self, event: str, args, _):
    arg = args[0]
    error = sys.exc_info()[1]
    author = getattr(arg, "author", self.bot.user)
    guild = getattr(arg, "guild", None)
    mock_ctx = ContextMock(self.bot, arg)

    if isinstance(error, commands.CommandInvokeError):
      error = error.original

    if await common_error_handling(mock_ctx, error):
      return True

    output = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    logger.error(output)

    if event == "on_application_command_autocomplete":
      await self.handle_context_error(arg, error, output)
    else:
      log_channel = self.bot.get_channel(config.base.log_channel_id)
      if log_channel is None: return

      embed = create_embed(error=error, cmd_type=command_utils.CommandTypes.UNKNOWN_COMMAND, command=event, args=args, author=author, guild=guild, jump_url=None)
      await log_channel.send(embed=embed)

      output = string_manipulation.split_to_parts(output, 1900)
      if log_channel is not None:
        for message in output:
          await log_channel.send(f"```\n{message}\n```")

    return True

  async def command_error_handling(self, ctx, error):
    if isinstance(error, commands.CommandInvokeError):
      error = error.original

    if not await common_error_handling(ctx, error):
      self.bot.last_error = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

      output = "".join(traceback.format_exception(type(error), error, error.__traceback__))
      logger.error(output)

      await self.handle_context_error(ctx, error, output)
