from disnake.ext import commands

def guild_owner():
  async def predicate(ctx):
    if await ctx.bot.is_owner(ctx.author):
      return True

    if hasattr(ctx, "guild") and ctx.guild is not None and ctx.author.id == ctx.guild.owner_id:
      return True

    return False

  return commands.check(predicate)
