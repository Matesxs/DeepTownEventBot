import disnake

def is_discord_guild_owner(ctx):
  if ctx.bot.owner_id is not None and ctx.bot.owner_id == ctx.author.id:
    return True

  if not isinstance(ctx.author, disnake.Member):
    return False

  if hasattr(ctx, "guild") and ctx.guild is not None and ctx.author.id == ctx.guild.owner_id:
    return True

  return False