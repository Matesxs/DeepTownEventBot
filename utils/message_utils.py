import disnake
from disnake.ext import commands
from typing import Union, Iterable, Any, Optional
import datetime

from config import config
from utils import string_manipulation

async def generate_error_message(ctx: Union[commands.Context, disnake.abc.Messageable, disnake.Message, disnake.MessageInteraction, disnake.ModalInteraction, disnake.ApplicationCommandInteraction], text: str):
  if hasattr(ctx, "channel") and hasattr(ctx, "guild"):
    if isinstance(ctx.channel, disnake.abc.GuildChannel):
      if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
        return None

  response_embed = disnake.Embed(color=disnake.Color.dark_red(), title=":x: | Error", description=string_manipulation.truncate_string(text, 4000))
  if isinstance(ctx, (disnake.ModalInteraction, disnake.ApplicationCommandInteraction, disnake.MessageInteraction)):
    return await ctx.send(embed=response_embed, ephemeral=True)
  elif isinstance(ctx, disnake.Message):
    return await ctx.reply(embed=response_embed)
  else:
    return await ctx.send(embed=response_embed, delete_after=config.base.error_duration)

async def generate_success_message(ctx: Union[commands.Context, disnake.abc.Messageable, disnake.Message, disnake.MessageInteraction, disnake.ModalInteraction, disnake.ApplicationCommandInteraction], text: str):
  if hasattr(ctx, "channel") and hasattr(ctx, "guild"):
    if isinstance(ctx.channel, disnake.abc.GuildChannel):
      if not ctx.channel.permissions_for(ctx.guild.me).send_messages:
        return None

  response_embed = disnake.Embed(color=disnake.Color.green(), title=":white_check_mark: | Success", description=string_manipulation.truncate_string(text, 4000))
  if isinstance(ctx, (disnake.ModalInteraction, disnake.ApplicationCommandInteraction, disnake.MessageInteraction)):
    return await ctx.send(embed=response_embed, ephemeral=True)
  elif isinstance(ctx, disnake.Message):
    return await ctx.reply(embed=response_embed)
  else:
    return await ctx.send(embed=response_embed, delete_after=config.base.success_duration)

def add_author_footer(embed: disnake.Embed, author: Union[disnake.User, disnake.Member],
                      set_timestamp=True, additional_text: Union[Iterable[str], None] = None):
  if set_timestamp:
    embed.timestamp = datetime.datetime.now(datetime.UTC).replace(tzinfo=None)

  if additional_text is not None:
    embed.set_footer(icon_url=author.display_avatar.url, text=' | '.join((author.display_name, *additional_text)))
  else:
    embed.set_footer(icon_url=author.display_avatar.url, text=author.display_name)

  return embed

async def delete_message(bot: commands.AutoShardedBot, cnt: Any):
  try:
    if isinstance(cnt, commands.Context):
      if cnt.guild is not None or cnt.message.author.id == bot.user.id:
        await cnt.message.delete()
    else:
      if cnt.guild is not None or cnt.message.author.id == bot.user.id:
        await cnt.delete()
  except:
    pass

def get_delete_button(author: Optional[disnake.User | disnake.Member] = None):
  if author is None:
    return disnake.ui.Button(emoji="🗑️", style=disnake.ButtonStyle.red, custom_id="msg_delete")
  else:
    return disnake.ui.Button(emoji="🗑️", style=disnake.ButtonStyle.red, custom_id=f"msg_delete:{author.id}")
