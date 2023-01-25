from disnake.ext import commands

from config import config
from database.discord_objects_repo import get_or_create_discord_guild
from features import exceptions

async def is_bot_developer(bot, user):
  if await bot.is_owner(user):
    return True

  if user.id in config.base.developer_ids:
    return True

  return False

async def predicate_bot_developer(ctx):
  if await is_bot_developer(ctx.bot, ctx.author):
    return True

  raise exceptions.NotBotDeveloper()

def bot_developer():
  return commands.check(predicate_bot_developer)

async def predicate_is_guild_owner(ctx):
  if await is_bot_developer(ctx.bot, ctx.author):
    return True

  if hasattr(ctx, "guild") and ctx.guild is not None and ctx.author.id == ctx.guild.owner_id:
    return True

  raise exceptions.NotGuildAdministrator()

def guild_owner():
  return commands.check(predicate_is_guild_owner)

async def predicate_is_guild_administrator(ctx):
  if await is_bot_developer(ctx.bot, ctx.author):
    return True

  if not hasattr(ctx, "guild") or ctx.guild is None:
    raise exceptions.NotGuildAdministrator()

  if ctx.author.id == ctx.guild.owner_id:
    return True

  guild_admin_role_id = (await get_or_create_discord_guild(ctx.guild)).admin_role_id
  if guild_admin_role_id is None:
    raise exceptions.NoGuildAdministratorRole()

  author_role_ids = [role.id for role in ctx.author.roles]
  if int(guild_admin_role_id) in author_role_ids:
    return True

  raise exceptions.NotGuildAdministrator()

def guild_administrator():
  return commands.check(predicate_is_guild_administrator)
