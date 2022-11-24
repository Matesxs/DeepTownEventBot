import disnake

def is_administrator(ctx):
  if ctx.bot.owner_id == ctx.author.id:
    return True

  if not isinstance(ctx.author, disnake.Member):
    return False

  if ctx.author.id == ctx.guild.owner_id:
    return True

  return False