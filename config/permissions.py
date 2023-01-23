from disnake.ext import commands

from database.guilds_repo import get_or_create_discord_guild
from features import exceptions

async def predicate_is_guild_owner(ctx):
  if await ctx.bot.is_owner(ctx.author):
    return True

  if hasattr(ctx, "guild") and ctx.guild is not None and ctx.author.id == ctx.guild.owner_id:
    return True

  raise exceptions.NotGuildAdministrator()

def guild_owner():
  return commands.check(predicate_is_guild_owner)

async def predicate_is_guild_administrator(ctx):
  if await ctx.bot.is_owner(ctx.author):
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
