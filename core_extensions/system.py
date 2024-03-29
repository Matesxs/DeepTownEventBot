# Administration extension

import disnake
from disnake.ext import commands
import asyncio
import math
from typing import Optional

from config import Strings, config
from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from features.views.paginator import EmbedView
from features.base_bot import BaseAutoshardedBot
from utils import command_utils, message_utils, string_manipulation
from features.git_manipulation import Git

logger = setup_custom_logger(__name__)

global_bot_reference: Optional[BaseAutoshardedBot] = None


async def unloaded_cogs_autocomplete(_, search: str):
  loaded_cogs = [str(cog.file) for cog in global_bot_reference.cogs.values()]
  all_cogs = command_utils.get_cogs_in_folder("extensions")
  all_cogs.extend(command_utils.get_cogs_in_folder("core_extensions"))

  unloaded_cogs = [cog for cog in all_cogs if cog not in loaded_cogs]

  if search is None or search == "":
    unloaded_cogs.append("all")
    return unloaded_cogs[:25]

  ret = [cog for cog in unloaded_cogs if search.lower() in cog.lower()]
  ret.append("all")
  return ret[:25]


async def loaded_cogs_autocomplete(_, search: str):
  loaded_cogs = [str(cog.file) for cog in global_bot_reference.cogs.values()]

  if search is None or search == "":
    loaded_cogs.append("all")
    return loaded_cogs[:25]

  ret = [cog for cog in loaded_cogs if search.lower() in cog.lower()]
  ret.append("all")
  return ret[:25]


async def loaded_cogs_not_protected_autocomplete(_, search: str):
  loaded_cogs = [str(cog.file) for cog in global_bot_reference.cogs.values() if str(cog.file) not in command_utils.get_cogs_in_folder("core_extensions")]

  if search is None or search == "":
    loaded_cogs.append("all")
    return loaded_cogs[:25]

  ret = [cog for cog in loaded_cogs if search.lower() in cog.lower()]
  ret.append("all")
  return ret[:25]

class System(Base_Cog):
  def __init__(self, bot):
    global global_bot_reference
    global_bot_reference = bot
    super(System, self).__init__(bot, __file__)

    self.git = Git()

  @command_utils.master_only_slash_command(name="system")
  @commands.is_owner()
  async def system_commands(self, inter: disnake.CommandInteraction):
    pass

  @system_commands.sub_command_group(name="status_messages")
  async def status_messages(self, inter: disnake.CommandInteraction):
    pass

  @status_messages.sub_command(name="set", description=Strings.system_status_messages_set_description)
  async def status_messages_set(self, inter: disnake.CommandInteraction,
                                status_messages: str = commands.Param(min_length=1, max_length=5000, description=Strings.system_status_messages_status_messages_param_description)):
    status_messages_list = status_messages.split(";")
    self.bot.presence_handler.set_messages(status_messages_list)
    await message_utils.generate_success_message(inter, Strings.system_status_messages_set_success)

  @status_messages.sub_command(name="set_with_default", description=Strings.system_status_messages_set_with_default_description)
  async def status_messages_set_with_default(self, inter: disnake.CommandInteraction,
                                status_messages: str = commands.Param(min_length=1, max_length=5000, description=Strings.system_status_messages_status_messages_param_description)):
    status_messages_list = status_messages.split(";")
    self.bot.presence_handler.set_messages(config.presence.status_messages + status_messages_list)
    await message_utils.generate_success_message(inter, Strings.system_status_messages_set_success)

  @status_messages.sub_command(name="reset", description=Strings.system_status_messages_reset_description)
  async def status_messages_reset(self, inter: disnake.CommandInteraction):
    self.bot.presence_handler.set_messages(config.presence.status_messages)
    await message_utils.generate_success_message(inter, Strings.system_status_messages_reset_success)

  @system_commands.sub_command_group(name="extensions")
  async def extensions(self, inter: disnake.CommandInteraction):
    pass

  @extensions.sub_command(name="load", description=Strings.system_load_description)
  async def load(self, inter: disnake.CommandInteraction, extension_name: str=commands.Param(autocomplete=unloaded_cogs_autocomplete, description="Name of extension to load")):
    cogs_in_extensions_folder = command_utils.get_cogs_in_folder("extensions")
    cogs_in_core_extensions_folder = command_utils.get_cogs_in_folder("core_extensions")

    if extension_name.lower() == "all":
      final_embed = disnake.Embed(title="Extensions loaded", color=disnake.Color.green(), description="Failed extensions:")

      loaded_cogs = [cog.file for cog in self.bot.cogs.values()]

      for cog in cogs_in_extensions_folder:
        if str(cog) not in loaded_cogs:
          try:
            self.bot.load_extension(f"extensions.{str(cog)}")
            logger.info(f"{str(cog)} loaded")
            await asyncio.sleep(0)
          except Exception as e:
            final_embed.description += f"\n{str(cog)}"
            final_embed.colour = disnake.Color.orange()

            await message_utils.generate_error_message(inter, Strings.system_unable_to_load_cog(cog=str(cog), e=e))

      for cog in cogs_in_core_extensions_folder:
        if str(cog) not in loaded_cogs:
          try:
            self.bot.load_extension(f"core_extensions.{str(cog)}")
            logger.info(f"{str(cog)} loaded")
            await asyncio.sleep(0)
          except Exception as e:
            final_embed.description += f"\n{str(cog)}"
            final_embed.colour = disnake.Color.orange()

            await message_utils.generate_error_message(inter, Strings.system_unable_to_load_cog(cog=str(cog), e=e))

      await inter.send(embed=final_embed, ephemeral=True)
    else:
      try:
        if extension_name in cogs_in_extensions_folder:
          self.bot.load_extension(f"extensions.{extension_name}")
        elif extension_name in cogs_in_core_extensions_folder:
          self.bot.load_extension(f"core_extensions.{extension_name}")
        else:
          return await message_utils.generate_error_message(inter, Strings.system_cog_not_found(extension=extension_name))

        logger.info(f"{extension_name} loaded")
        await message_utils.generate_success_message(inter, Strings.system_cog_loaded(extension=extension_name))
      except Exception as e:
        await message_utils.generate_error_message(inter, Strings.system_unable_to_load_cog(cog=extension_name, e=e))

  @extensions.sub_command(name="unload", description=Strings.system_unload_description)
  async def unload(self, inter: disnake.CommandInteraction, extension_name: str=commands.Param(autocomplete=loaded_cogs_not_protected_autocomplete, description="Name of extension to unload")):
    if extension_name in command_utils.get_cogs_in_folder("core_extensions"):
      return await message_utils.generate_error_message(inter, Strings.system_unload_protected_cog(extension=extension_name))

    if extension_name.lower() == "all":
      final_embed = disnake.Embed(title="Extensions unload", color=disnake.Color.green(), description="Failed extensions:")

      loaded_cogs = [cog.file for cog in self.bot.cogs.values()]

      for cog in loaded_cogs:
        if cog not in command_utils.get_cogs_in_folder("core_extensions"):
          try:
            self.bot.unload_extension(f"extensions.{cog}")
            logger.info(f'{cog} unloaded')
            await asyncio.sleep(0)
          except Exception as e:
            final_embed.description += f"\n{str(cog)}"
            final_embed.colour = disnake.Color.orange()

            await message_utils.generate_error_message(inter, Strings.system_unable_to_unload_cog(cog=cog, e=e))

      await inter.send(embed=final_embed, ephemeral=True)
    else:
      cogs_in_extensions_folder = command_utils.get_cogs_in_folder("extensions")

      try:
        if extension_name in cogs_in_extensions_folder:
          self.bot.unload_extension(f"extensions.{extension_name}")
        else:
          return await message_utils.generate_error_message(inter, Strings.system_cog_not_found(extension=extension_name))

        logger.info(f'{extension_name} unloaded')
        await message_utils.generate_success_message(inter, Strings.system_cog_unloaded(extension=extension_name))
      except Exception as e:
        await message_utils.generate_error_message(inter, Strings.system_unable_to_unload_cog(cog=extension_name, e=e))

  @extensions.sub_command(name="reload", description=Strings.system_reload_description)
  async def reload(self, inter: disnake.CommandInteraction, extension_name: str=commands.Param(autocomplete=loaded_cogs_autocomplete, description="Name of extension to reload")):
    loaded_cogs = [cog.file for cog in self.bot.cogs.values()]
    cogs_in_extensions_folder = command_utils.get_cogs_in_folder("extensions")
    cogs_in_core_extensions_folder = command_utils.get_cogs_in_folder("core_extensions")

    if extension_name.lower() == "all":
      final_embed = disnake.Embed(title="Extensions reloaded", color=disnake.Color.green(), description="Failed extensions:")

      for cog in loaded_cogs:
        try:
          if cog in cogs_in_extensions_folder:
            self.bot.reload_extension(f"extensions.{cog}")
          elif cog in cogs_in_core_extensions_folder:
            self.bot.reload_extension(f"core_extensions.{cog}")
          else:
            final_embed.description += f"\n{str(cog)}"
            final_embed.colour = disnake.Color.orange()
            continue

          logger.info(f"{cog} reloaded")
          await asyncio.sleep(0)
        except Exception as e:
          final_embed.description += f"\n{str(cog)}"
          final_embed.colour = disnake.Color.orange()

          await message_utils.generate_error_message(inter, Strings.system_unable_to_reload_cog(cog=cog, e=e))

      await inter.send(embed=final_embed, ephemeral=True)
    else:
      try:
        if extension_name in cogs_in_extensions_folder:
          self.bot.reload_extension(f"extensions.{extension_name}")
        elif extension_name in cogs_in_core_extensions_folder:
          self.bot.reload_extension(f"core_extensions.{extension_name}")
        else:
          return await message_utils.generate_error_message(inter, Strings.system_cog_not_found(extension=extension_name))

        logger.info(f"{extension_name} reloaded")

        await message_utils.generate_success_message(inter, Strings.system_cog_reloaded(extension=extension_name))
      except Exception as e:
        await message_utils.generate_error_message(inter, Strings.system_unable_to_reload_cog(cog=extension_name, e=e))

  @extensions.sub_command(name="list", description=Strings.system_cogs_description)
  async def cogs(self, inter: disnake.CommandInteraction):
    cogs_in_folder = command_utils.get_cogs_in_folder("extensions")
    protected_cogs_in_folder = command_utils.get_cogs_in_folder("core_extensions")
    cogs_in_folder.extend(protected_cogs_in_folder)

    loaded_cogs = [cog.file for cog in self.bot.cogs.values()]

    number_of_batches = math.ceil(len(cogs_in_folder) / 21)
    cogs_in_folder_batches = [cogs_in_folder[i * 21: i * 21 + 21] for i in range(number_of_batches)]

    pages = []
    for batch in cogs_in_folder_batches:
      embed = disnake.Embed(title="Cogs", description="List of all loaded and unloaded cogs", color=disnake.Color.dark_magenta())

      for idx, cog in enumerate(batch):
        status = "🔒 *protected*" if cog in protected_cogs_in_folder else ("✅ **loaded**" if cog in loaded_cogs else "❌ **unloaded**")
        embed.add_field(name=cog, value=status)

      pages.append(embed)

    await EmbedView(inter.author, pages, perma_lock=True).run(inter)

  @system_commands.sub_command(description=Strings.system_logout_description)
  async def logout(self, inter: disnake.CommandInteraction):
    await inter.send("Cya :wave:")
    await self.bot.close()

  @system_commands.sub_command(description=Strings.system_update_description)
  async def update(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    result = str(await self.git.pull())
    if "Already up to date." in result:
      return await message_utils.generate_success_message(inter, Strings.system_update_already_up_to_date)

    result_message_lines = result.split("\n")
    while result_message_lines:
      result_message, result_message_lines = string_manipulation.add_string_until_length(result_message_lines, 1900, "\n")
      await inter.send(f"Git pull result\n```diff\n{result_message}\n```")

    await inter.send("Cya :wave:")
    await self.bot.close()

  @system_commands.sub_command(name="pull", description=Strings.system_git_pull_description)
  async def git_pull(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    result_message_lines = str(await self.git.pull()).split("\n")
    while result_message_lines:
      result_message, result_message_lines = string_manipulation.add_string_until_length(result_message_lines, 1900, "\n")
      await inter.send(f"Git pull result\n```diff\n{result_message}\n```")


def setup(bot):
  bot.add_cog(System(bot))
