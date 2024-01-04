# Custom help extension

import dataclasses
import asyncio
import disnake
from disnake.ext import commands
from typing import Set

from config import config, cooldowns, Strings
from features.views.paginator import EmbedView
from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from typing import List, Optional
from utils import command_utils, string_manipulation, message_utils

logger = setup_custom_logger(__name__)

@dataclasses.dataclass
class CommandDescriptor:
  signature: str
  description: str

@dataclasses.dataclass
class CommandGroup:
  name: Optional[str]
  description: Optional[str]
  commands: List[CommandDescriptor]

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

def generate_com_help(com):
  help_string = f"**Help**: " + com.help if com.help is not None else ""
  brief = f"**Brief**: {com.brief}" if com.brief is not None else ""
  aliases = ("**Aliases**: " + ", ".join(com.aliases)) + "" if com.aliases else ""

  string_array = [it for it in [aliases, brief, help_string] if it != ""]
  output = "\n".join(string_array) if string_array else "*No description*"

  return f"{config.base.command_prefix}{command_utils.get_text_command_signature(com)}", string_manipulation.truncate_string(output, 4000)


async def generate_message_command_data(cogs: List[Base_Cog], ctx) -> List[CommandGroup]:
  data = []

  for cog in cogs:
    if cog.hidden: continue

    coms = [com for com in cog.walk_commands() if isinstance(com, commands.Command) and not com.hidden and await command_check(com, ctx)]
    if not coms: continue

    coms_data = [generate_com_help(com) for com in coms]

    command_descriptiors = [CommandDescriptor(signature, description) for signature, description in coms_data]
    data.append(CommandGroup(str(cog.qualified_name), None, command_descriptiors))
  return data

def generate_help_pages(command_descriptors: List[CommandGroup], author: disnake.User) -> List[disnake.Embed]:
  pages = []

  for descriptor in command_descriptors:
    title = f"{string_manipulation.truncate_string(str(descriptor.name) if descriptor.name is not None else 'Free commands', 250)} Help"
    emb = disnake.Embed(title=title, colour=disnake.Color.green(), description=descriptor.description if descriptor.description is not None and descriptor.description != "-" else None)
    message_utils.add_author_footer(emb, author)
    commands_data = descriptor.commands
    if not commands_data: continue

    while commands_data:
      command_data = commands_data.pop()
      embed_len = len(emb)
      added_length = len(command_data.signature) + len(command_data.description)

      if embed_len + added_length > 6000:
        pages.append(emb)
        emb = disnake.Embed(title=title, colour=disnake.Color.green())
        message_utils.add_author_footer(emb, author)

      emb.add_field(name=command_data.signature, value=command_data.description, inline=False)
    pages.append(emb)

  return pages

async def generate_slash_command_data(slash_commands: Set[commands.InvokableSlashCommand], ctx) -> List[CommandGroup]:
  free_commands = []
  command_groups = []

  def value_options_to_string(option_list: List[disnake.Option]):
    options_strings = []

    for option in option_list:
      if option.required:
        options_strings.append(f"<{option.name}>")
      else:
        options_strings.append(f"[{option.name}]")

    return " ".join(options_strings)

  for slash_command in slash_commands:
    if slash_command.guild_ids is not None and slash_command.guild_ids:
      if ctx.guild is None or ctx.guild.id not in slash_command.guild_ids:
        continue

    if not (await command_check(slash_command, ctx)):
      continue

    option_types = [op.type for op in slash_command.options]
    if disnake.OptionType.sub_command not in option_types and disnake.OptionType.sub_command_group not in option_types:
      free_commands.append(CommandDescriptor(f"/{slash_command.name} {value_options_to_string(slash_command.options)}", slash_command.description))
    else:
      group_commands = []
      for sc_option in slash_command.options:
        if sc_option.type == disnake.OptionType.sub_command_group:
          for scg_option in sc_option.options:
            if scg_option.type == disnake.OptionType.sub_command:
              group_commands.append(CommandDescriptor(f"/{slash_command.name} {sc_option.name} {scg_option.name} {value_options_to_string(scg_option.options)}", scg_option.description))
        elif sc_option.type == disnake.OptionType.sub_command:
          group_commands.append(CommandDescriptor(f"/{slash_command.name} {sc_option.name} {value_options_to_string(sc_option.options)}", sc_option.description))
      command_groups.append(CommandGroup(slash_command.name, slash_command.description, group_commands))

  return [CommandGroup(None, None, free_commands), *command_groups]

class Help(Base_Cog):
  def __init__(self, bot):
    super(Help, self).__init__(bot, __file__)

  @commands.slash_command(name="help", description=Strings.help_description)
  @cooldowns.short_cooldown
  async def help(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    command_descriptiors = [*(await generate_slash_command_data(self.bot.slash_commands, inter)), *(await generate_message_command_data(self.bot.cogs.values(), inter))]
    pages = generate_help_pages(command_descriptiors, inter.author)

    if pages:
      await EmbedView(inter.author, embeds=pages).run(inter)
    else:
      emb = disnake.Embed(title="Help", description="*No help available*", colour=disnake.Color.orange())
      await inter.send(embed=emb)

def setup(bot):
  bot.add_cog(Help(bot))
