# Custom help extension

import asyncio
import disnake
from disnake.ext import commands
from typing import Set

from config import config, cooldowns, Strings
from features.views.paginator import EmbedView
from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from typing import Union, List, Optional
from features.base_bot import BaseAutoshardedBot
from utils import command_utils, string_manipulation, message_utils

logger = setup_custom_logger(__name__)

async def command_check(com, ctx):
  if not com.checks:
    return True

  for check in com.checks:
    try:
      if asyncio.iscoroutinefunction(check):
        result = await check(ctx)
        if not result:
          return False
      else:
        if not check(ctx):
          return False
    except Exception:
      return False

  return True

async def get_all_commands(bot: BaseAutoshardedBot, ctx):
  return [com for cog in bot.cogs.values() for com in cog.walk_commands() if isinstance(com, commands.Command) and not com.hidden and await command_check(com, ctx)]

async def help_name_autocomplete(inter, string):
  everything = [str(cog.qualified_name).replace("_", " ") for cog in inter.bot.cogs.values()]
  everything.extend([com.name for com in await get_all_commands(inter.bot, inter)])

  if string is None or string == "":
    return everything[:25]
  return [d for d in everything if string.lower() in d.lower()][:25]

def generate_com_help(com):
  help_string = f"**Help**: " + com.help if com.help is not None else ""
  brief = f"**Brief**: {com.brief}" if com.brief is not None else ""
  aliases = ("**Aliases**: " + ", ".join(com.aliases)) + "" if com.aliases else ""

  string_array = [it for it in [aliases, brief, help_string] if it != ""]
  output = "\n".join(string_array) if string_array else "*No description*"

  return f"{config.base.command_prefix}{command_utils.get_command_signature(com)}", string_manipulation.truncate_string(output, 4000)

def add_command_help(embed, com):
  signature, description = generate_com_help(com)
  embed.add_field(name=signature, value=description, inline=False)


async def generate_help_for_cog(cog: Base_Cog, ctx) -> Union[None, List[disnake.Embed]]:
  if cog.hidden: return None

  coms = [com for com in cog.walk_commands() if isinstance(com, commands.Command) and not com.hidden and await command_check(com, ctx)]
  number_of_coms = len(coms)
  if number_of_coms == 0: return None

  coms = [generate_com_help(com) for com in coms]

  pages = []
  title = f"{str(cog.qualified_name)} Help"
  emb = disnake.Embed(title=title, colour=disnake.Color.green())
  message_utils.add_author_footer(emb, ctx.author)

  while coms:
    signature, description = coms.pop()
    embed_len = len(emb)
    added_length = len(signature) + len(description)

    if embed_len + added_length > 5000:
      pages.append(emb)
      emb = disnake.Embed(title=title, colour=disnake.Color.green())
      message_utils.add_author_footer(emb, ctx.author)

    emb.add_field(name=signature, value=description, inline=False)

  pages.append(emb)

  return pages

def parse_slash_commands(slash_commands: Set[commands.InvokableSlashCommand]):
  command_strings = []

  def value_options_to_string(option_list: List[disnake.Option]):
    options_strings = []

    for option in option_list:
      if option.required:
        options_strings.append(f"<{option.name}>")
      else:
        options_strings.append(f"[{option.name}]")

    return " ".join(options_strings)

  for slash_command in slash_commands:
    option_types = [op.type for op in slash_command.options]
    if disnake.OptionType.sub_command not in option_types and disnake.OptionType.sub_command_group not in option_types:
      command_strings.append((f"/{slash_command.name} {value_options_to_string(slash_command.options)}", slash_command.description))
    else:
      for sc_option in slash_command.options:
        if sc_option.type == disnake.OptionType.sub_command_group:
          for scg_option in sc_option.options:
            if scg_option.type == disnake.OptionType.sub_command:
              command_strings.append((f"/{slash_command.name} {sc_option.name} {scg_option.name} {value_options_to_string(scg_option.options)}", scg_option.description))
        elif sc_option.type == disnake.OptionType.sub_command:
          command_strings.append((f"/{slash_command.name} {sc_option.name} {value_options_to_string(sc_option.options)}", sc_option.description))

  return command_strings

class Help(Base_Cog):
  def __init__(self, bot):
    super(Help, self).__init__(bot, __file__)

  @commands.slash_command(name="help", description=Strings.help_description)
  @cooldowns.short_cooldown
  async def help(self, inter: disnake.CommandInteraction, name: Optional[str]=commands.Param(default=None, description=Strings.help_name_param_description, autocomplete=help_name_autocomplete)):
    pages = []
    if name is not None:
      all_commands = await get_all_commands(self.bot, inter)
      command = disnake.utils.get(all_commands, name=name)
      if command is not None:
        emb = disnake.Embed(title="Help", colour=disnake.Color.green())
        message_utils.add_author_footer(emb, inter.author)
        add_command_help(emb, command)
        return await inter.send(embed=emb)

    for cog in self.bot.cogs.values():
      if name is not None:
        if name.lower() != cog.qualified_name.lower() and \
            name.lower() != cog.file.lower() and \
            name.lower() != cog.file.lower().replace("_", " "):
          continue

      cog_pages = await generate_help_for_cog(cog, inter)
      if cog_pages is not None:
        pages.extend(cog_pages)

    if pages:
      await EmbedView(inter.author, embeds=pages, perma_lock=True).run(inter)
    else:
      emb = disnake.Embed(title="Help", description="*No help available*", colour=disnake.Color.orange())
      await inter.send(embed=emb)

  @commands.slash_command(name="slash_command_list", description=Strings.help_slash_command_list_description)
  @cooldowns.short_cooldown
  async def slash_command_list(self, inter: disnake.CommandInteraction):
    slash_command_strings = parse_slash_commands(self.bot.slash_commands)
    if not slash_command_strings:
      return await message_utils.generate_error_message(inter, Strings.help_slash_command_list_no_slash_commands)

    pages = []
    embed = disnake.Embed(title="Slash command list", color=disnake.Color.green())
    message_utils.add_author_footer(embed, inter.author)

    while slash_command_strings:
      signature, description = slash_command_strings.pop(0)

      embed_len = len(embed)
      added_length = len(signature) + len(description)

      if embed_len + added_length > 2000:
        pages.append(embed)
        embed = disnake.Embed(title="Slash command list", colour=disnake.Color.green())
        message_utils.add_author_footer(embed, inter.author)

      embed.add_field(name=signature, value=description, inline=False)

    pages.append(embed)

    if pages:
      await EmbedView(inter.author, embeds=pages, perma_lock=True).run(inter)
    else:
      await message_utils.generate_error_message(inter, Strings.help_slash_command_list_no_slash_commands)

def setup(bot):
  bot.add_cog(Help(bot))
