from disnake.ext import commands

from config import config
from database.discord_objects_repo import get_or_create_discord_guild
from features import exceptions

async def is_bot_developer(ctx):
  if await ctx.bot.is_owner(ctx.author):
    return True

  if ctx.author.id in config.base.developer_ids:
    return True

  return False

def is_guild_administrator(ctx):
  if hasattr(ctx, "guild") and ctx.guild is not None:
    if ctx.author.guild_permissions.administrator:
      return True

    if ctx.guild is not None and ctx.author.id == ctx.guild.owner_id:
      return True
  return False

async def has_guild_administrator_role(ctx):
  if await is_bot_developer(ctx):
    return True

  if hasattr(ctx, "guild") and ctx.guild is not None:
    if is_guild_administrator(ctx):
      return True

    guild_admin_role_id = (await get_or_create_discord_guild(ctx.guild)).admin_role_id
    if guild_admin_role_id is None:
      return False

    author_role_ids = [role.id for role in ctx.author.roles]
    if int(guild_admin_role_id) in author_role_ids:
      return True

  return False

async def __predicate_bot_developer(ctx):
  if await is_bot_developer(ctx):
    return True

  raise exceptions.NotBotDeveloper()

async def __predicate_is_guild_owner(ctx):
  if await is_bot_developer(ctx):
    return True

  if is_guild_administrator(ctx):
    return True

  raise exceptions.NotGuildAdministrator()

async def __predicate_guild_administrator_role(ctx):
  if await is_bot_developer(ctx):
    return True

  if not hasattr(ctx, "guild") or ctx.guild is None:
    raise exceptions.NotGuildAdministrator()

  if is_guild_administrator(ctx):
    return True

  guild_admin_role_id = (await get_or_create_discord_guild(ctx.guild)).admin_role_id
  if guild_admin_role_id is None:
    raise exceptions.NoGuildAdministratorRoleAndNotSet()

  author_role_ids = [role.id for role in ctx.author.roles]
  if int(guild_admin_role_id) in author_role_ids:
    return True

  raise exceptions.NotGuildAdministrator()

def bot_developer():
  return commands.check(__predicate_bot_developer)

def guild_administrator():
  return commands.check(__predicate_is_guild_owner)

def guild_administrator_role():
  return commands.check(__predicate_guild_administrator_role)
