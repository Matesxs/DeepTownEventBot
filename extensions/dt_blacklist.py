import asyncio
import disnake
from disnake.ext import commands, tasks
from typing import Optional
import re

from config import cooldowns, Strings, config
from features.base_cog import Base_Cog
from features.views.paginator import EmbedView
from database import dt_blacklist_repo, dt_user_repo, dt_guild_repo
from utils import message_utils, string_manipulation, object_getters
from table2ascii import table2ascii, Alignment

id_in_identifier_regex = re.compile(r"([A-Z]*) .*\((\d*)\).*")

class DTBlacklist(Base_Cog):
  def __init__(self, bot):
    super(DTBlacklist, self).__init__(bot, __file__)

    self.identificators = [f"USER {user.username} ({user.id})" for user in dt_user_repo.get_all_users()]
    self.identificators.extend([f"GUILD {guild.name} ({guild.id})" for guild in dt_guild_repo.get_all_guilds()])
    if not self.update_identificators_task.is_running():
      self.update_identificators_task.start()

  def cog_unload(self) -> None:
    if self.update_identificators_task.is_running():
      self.update_identificators_task.cancel()

  @commands.slash_command(name="blacklist")
  async def blacklist_commands(self, inter: disnake.CommandInteraction):
    pass

  @blacklist_commands.sub_command(name="add", description=Strings.blacklist_add_description)
  @cooldowns.default_cooldown
  @commands.is_owner()
  async def blacklist_add(self, inter: disnake.CommandInteraction,
                          type: dt_blacklist_repo.BlacklistType=commands.Param(description=Strings.blacklist_type_param_description),
                          identifier: int=commands.Param(description=Strings.blacklist_identifier_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)
    type = dt_blacklist_repo.BlacklistType(type)

    if dt_blacklist_repo.get_blacklist_item(type, identifier) is not None:
      return await message_utils.generate_error_message(inter, Strings.blacklist_add_already_on_blacklist)

    if type == dt_blacklist_repo.BlacklistType.USER:
      subject = dt_user_repo.get_dt_user(identifier)
      subject_name = subject.username if subject is not None else None
    elif type == dt_blacklist_repo.BlacklistType.GUILD:
      subject = dt_guild_repo.get_dt_guild(identifier)
      subject_name = subject.name if subject is not None else None
    else:
      return await message_utils.generate_error_message(inter, Strings.blacklist_add_invalid_type)

    if subject is None:
      return await message_utils.generate_error_message(inter, Strings.blacklist_add_subject_not_found)

    dt_blacklist_repo.create_blacklist_item(type, identifier, subject_name)
    await asyncio.sleep(0.1)

    if type == dt_blacklist_repo.BlacklistType.USER:
      dt_user_repo.remove_user(identifier)
    elif type == dt_blacklist_repo.BlacklistType.GUILD:
      dt_guild_repo.remove_guild(identifier)

    await message_utils.generate_success_message(inter, Strings.blacklist_add_success(subject_name=subject_name, type=type))

  @blacklist_commands.sub_command(name="remove", description=Strings.blacklist_remove_description)
  @cooldowns.default_cooldown
  @commands.is_owner()
  async def blacklist_remove(self, inter: disnake.CommandInteraction,
                          type: dt_blacklist_repo.BlacklistType = commands.Param(description=Strings.blacklist_type_param_description),
                          identifier: int = commands.Param(description=Strings.blacklist_identifier_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)
    type = dt_blacklist_repo.BlacklistType(type)

    if dt_blacklist_repo.remove_blacklist_item(type, identifier):
      await message_utils.generate_success_message(inter, Strings.blacklist_remove_success(identifier=identifier, type=type))
    else:
      await message_utils.generate_error_message(inter, Strings.blacklist_remove_failed(identifier=identifier, type=type))

  @blacklist_commands.sub_command(name="list", description=Strings.blacklist_list_description)
  @cooldowns.default_cooldown
  async def blacklist_list(self, inter: disnake.CommandInteraction,
                           type: Optional[dt_blacklist_repo.BlacklistType] = commands.Param(default=None, description=Strings.blacklist_type_param_description)):
    await inter.response.defer(with_message=True)

    if type is not None:
      type = dt_blacklist_repo.BlacklistType(type)

    blacklist_items = dt_blacklist_repo.get_blacklist_items(type)

    blacklist_data = [(bitem.identifier, bitem.bl_type, bitem.additional_data) for bitem in blacklist_items]
    blacklist_table_lines = table2ascii(["Identifier", "Type", "Specific Data"], blacklist_data, alignments=[Alignment.LEFT, Alignment.LEFT, Alignment.LEFT]).split("\n")

    blacklist_pages = []
    while blacklist_table_lines:
      output_string, blacklist_table_lines = string_manipulation.add_string_until_length(blacklist_table_lines, 2000, "\n")
      embed = disnake.Embed(title="Blacklist", description=f"```\n{output_string}\n```", color=disnake.Color.orange())
      message_utils.add_author_footer(embed, inter.author)
      blacklist_pages.append(embed)

    embed_view = EmbedView(inter.author, blacklist_pages)
    await embed_view.run(inter)

  @blacklist_commands.sub_command(description="Report cheater to bot administrator")
  @cooldowns.long_cooldown
  async def report_cheater(self, inter: disnake.CommandInteraction,
                           identifier: str=commands.Param(description="Identifier of entity to report"),
                           reason: Optional[str]=commands.Param(default=None, description="Optional reason why you think this entity is cheating", max_length=3000)):
    await inter.response.defer(with_message=True, ephemeral=True)

    announce_channel = await object_getters.get_or_fetch_channel(self.bot, config.blacklist.report_channel_id)
    if announce_channel is None:
      return await message_utils.generate_error_message(inter, "Report channel not found, unable to report cheater")

    specifier = id_in_identifier_regex.findall(identifier)
    if len(specifier) != 1 or len(specifier[0]) != 2 or not str(specifier[0][1]).isnumeric():
      return await message_utils.generate_error_message(inter, "Invalid identifier entered")
    specifier = specifier[0]

    if specifier[0] == "USER":
      user = dt_user_repo.get_dt_user(int(specifier[1]))
      if user is None:
        return await message_utils.generate_error_message(inter, "User not found in database")

      embed = disnake.Embed(title="User cheater report", color=disnake.Color.orange(), description=f"```\n{reason}\n```" if reason is not None else None)
      message_utils.add_author_footer(embed, inter.author)
      embed.add_field(name="Username", value=user.username)
      embed.add_field(name="ID", value=str(user.id))
      embed.add_field(name="Guild", value=f"{user.active_member.guild.name}" if user.active_member is not None else "None")
    elif specifier[0] == "GUILD":
      guild = dt_guild_repo.get_dt_guild(int(specifier[1]))
      if guild is None:
        return await message_utils.generate_error_message(inter, "Guild not found in database")

      embed = disnake.Embed(title="Guild cheater report", color=disnake.Color.orange(), description=f"```\n{reason}\n```" if reason is not None else None)
      message_utils.add_author_footer(embed, inter.author)
      embed.add_field(name="Name", value=guild.name)
      embed.add_field(name="ID", value=str(guild.id))
    else:
      return await message_utils.generate_error_message(inter, "Invalid report class")

    await announce_channel.send(embed=embed)
    await message_utils.generate_success_message(inter, "Report submited")

  @report_cheater.autocomplete("identifier")
  async def autocomplete_identifier_user_and_guild(self, _, string: str):
    if string is None or not string:
      return self.identificators[:25]
    return [i for i in self.identificators if string.lower() in i.lower()][:25]

  @tasks.loop(minutes=30)
  async def update_identificators_task(self):
    await asyncio.sleep(30)
    new_identificators = [f"USER {user.username} ({user.id})" for user in dt_user_repo.get_all_users()]
    new_identificators.extend([f"GUILD {guild.name} ({guild.id})" for guild in dt_guild_repo.get_all_guilds()])
    self.identificators = new_identificators

def setup(bot):
  bot.add_cog(DTBlacklist(bot))
