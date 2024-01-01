# Error handling extension

import datetime
import disnake
from disnake.ext import commands
import traceback
import sqlalchemy.exc

from database import session
from utils import message_utils, command_utils, string_manipulation
from utils.logger import setup_custom_logger
from features.base_cog import Base_Cog
from config import config, Strings
from features.base_bot import BaseAutoshardedBot
from features import exceptions

logger = setup_custom_logger(__name__)

class Errors(Base_Cog):
  def __init__(self, bot: BaseAutoshardedBot):
    super(Errors, self).__init__(bot, __file__)

  @commands.Cog.listener()
  async def on_command_error(self, ctx: commands.Context, error):
    await self.command_error_handling(ctx, error)

  @commands.Cog.listener()
  async def on_slash_command_error(self, inter: disnake.ApplicationCommandInteraction, error):
    await self.command_error_handling(inter, error)

  @commands.Cog.listener()
  async def on_user_command_error(self, inter: disnake.ApplicationCommandInteraction, error):
    await self.command_error_handling(inter, error)

  @commands.Cog.listener()
  async def on_message_command_error(self, inter: disnake.ApplicationCommandInteraction, error):
    await self.command_error_handling(inter, error)

  async def command_error_handling(self, ctx, error):
    if isinstance(error, commands.CommandInvokeError):
      error = error.original

    if isinstance(error, disnake.errors.DiscordServerError):
      pass
    elif isinstance(error, sqlalchemy.exc.InternalError) or isinstance(error, sqlalchemy.exc.IntegrityError):
      logger.warning(f"Database rollback")
      output = "".join(traceback.format_exception(type(error), error, error.__traceback__))
      logger.error(output)

      session.rollback()
    elif isinstance(error, disnake.Forbidden):
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
    elif isinstance(error, disnake.NotFound):
      await message_utils.generate_error_message(ctx, Strings.error_not_found(code=error.code, text=error.text))
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
      await message_utils.generate_error_message(ctx, Strings.error_missing_argument(argument=error.param, signature=command_utils.get_command_signature(ctx)))
    elif isinstance(error, commands.BadArgument):
      await message_utils.generate_error_message(ctx, Strings.error_bad_argument)
    elif isinstance(error, commands.MaxConcurrencyReached):
      await message_utils.generate_error_message(ctx, Strings.error_max_concurrency_reached)
    elif isinstance(error, commands.NoPrivateMessage):
      await message_utils.generate_error_message(ctx, Strings.error_no_private_message)
    elif isinstance(error, disnake.InteractionTimedOut):
      await message_utils.generate_error_message(ctx, Strings.error_interaction_timeout)
    else:
      self.bot.last_error = datetime.datetime.utcnow()

      output = "".join(traceback.format_exception(type(error), error, error.__traceback__))
      logger.error(output)

      log_channel = self.bot.get_channel(config.base.log_channel_id)
      if log_channel is None: return

      if hasattr(ctx, "application_command") and ctx.application_command is not None:
        embed = disnake.Embed(title=f"Ignoring exception in application interaction {ctx.application_command}", color=0xFF0000)
      elif hasattr(ctx, "command") and ctx.command is not None:
        embed = disnake.Embed(title=f"Ignoring exception in command {ctx.command}", color=0xFF0000)
      else:
        embed = disnake.Embed(title=f"Ignoring exception", color=0xFF0000)

      if hasattr(ctx, "message") and ctx.message is not None:
        embed.add_field(name="Message", value=ctx.message.content[:1000])
        embed.add_field(name="Link", value=ctx.message.jump_url, inline=False)

      if hasattr(ctx, "author") and ctx.author is not None:
        embed.add_field(name="Autor", value=str(ctx.author))

      embed.add_field(name="Type", value=str(type(error)))

      if hasattr(ctx, "guild") and ctx.guild is not None:
        embed.add_field(name="Guild", value=ctx.guild.name)

      await log_channel.send(embed=embed)

      output = string_manipulation.split_to_parts(output, 1900)
      if log_channel is not None:
        for message in output:
          await log_channel.send(f"```\n{message}\n```")

      try:
        await message_utils.generate_error_message(ctx, Strings.error_unknown_error)
      except:
        pass


def setup(bot):
  bot.add_cog(Errors(bot))
