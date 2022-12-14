import asyncio
import disnake
from disnake.ext import commands
from typing import Optional

from config import cooldowns, Strings, config
from features.base_cog import Base_Cog
from features.views.paginator import EmbedView
from database import dt_blacklist_repo, dt_user_repo, dt_guild_repo
from utils import message_utils, string_manipulation, object_getters, dt_identifier_autocomplete
from table2ascii import table2ascii, Alignment

class DTBlacklist(Base_Cog):
  def __init__(self, bot):
    super(DTBlacklist, self).__init__(bot, __file__)

  @commands.slash_command(name="blacklist")
  async def blacklist_commands(self, inter: disnake.CommandInteraction):
    pass

  @staticmethod
  async def add_to_blacklist(inter, block_type: dt_blacklist_repo.BlacklistType, entity_id: int) -> bool:
    if dt_blacklist_repo.is_on_blacklist(block_type, entity_id):
      await message_utils.generate_error_message(inter, Strings.blacklist_add_already_on_blacklist)
      return False

    if block_type == dt_blacklist_repo.BlacklistType.USER:
      subject = dt_user_repo.get_dt_user(entity_id)
      subject_name = subject.username if subject is not None else None
    else:
      subject = dt_guild_repo.get_dt_guild(entity_id)
      subject_name = subject.name if subject is not None else None

    if subject is None:
      await message_utils.generate_error_message(inter, Strings.blacklist_add_subject_not_found)
      return False

    dt_blacklist_repo.create_blacklist_item(block_type, entity_id, subject_name)
    await asyncio.sleep(0.1)

    if block_type == dt_blacklist_repo.BlacklistType.USER:
      dt_user_repo.remove_user(entity_id)
    elif block_type == dt_blacklist_repo.BlacklistType.GUILD:
      dt_guild_repo.remove_guild(entity_id)

    await message_utils.generate_success_message(inter, Strings.blacklist_add_success(subject_name=subject_name, type=block_type))
    return True

  @blacklist_commands.sub_command(name="add", description=Strings.blacklist_add_description)
  @cooldowns.default_cooldown
  @commands.is_owner()
  async def blacklist_add(self, inter: disnake.CommandInteraction,
                          identifier: str=commands.Param(description=Strings.blacklist_identifier_param_description, autocomp=dt_identifier_autocomplete.autocomplete_identifier_guild_and_user)):
    await inter.response.defer(with_message=True, ephemeral=True)

    specifier = dt_identifier_autocomplete.identifier_to_specifier(identifier)
    if specifier is None:
      return await message_utils.generate_error_message(inter, Strings.blacklist_add_invalid_identifier)

    block_type, entity_id = specifier
    if block_type == "USER":
      block_type = dt_blacklist_repo.BlacklistType.USER
    elif block_type == "GUILD":
      block_type = dt_blacklist_repo.BlacklistType.GUILD
    else:
      return await message_utils.generate_error_message(inter, Strings.blacklist_add_invalid_type)

    await self.add_to_blacklist(inter, block_type, entity_id)

  @commands.message_command(name="Add to Blacklist")
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def msg_com_add_to_blacklist(self, inter: disnake.MessageCommandInteraction):
    target_message = inter.target

    if len(target_message.embeds) != 1 or target_message.author.id != self.bot.user.id:
      return await message_utils.generate_error_message(inter, Strings.blacklist_msg_com_add_invalid_target)

    report_embed = target_message.embeds[0]

    if not "report" in report_embed.title.lower():
      return await message_utils.generate_error_message(inter, Strings.blacklist_msg_com_add_invalid_target)

    if "user" in report_embed.title.lower():
      blacklist_type = dt_blacklist_repo.BlacklistType.USER
    elif "guild" in report_embed.title.lower():
      blacklist_type = dt_blacklist_repo.BlacklistType.GUILD
    else:
      return await message_utils.generate_error_message(inter, Strings.blacklist_msg_com_add_invalid_target)

    for field in report_embed.fields:
      if "id" in field.name.lower() and field.value.isnumeric():
        entity_id = int(field.value)
        result = await self.add_to_blacklist(inter, blacklist_type, entity_id)
        if result:
          try:
            await target_message.delete()
          except:
            pass
        return

    return await message_utils.generate_error_message(inter, Strings.blacklist_msg_com_add_invalid_target)

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

    blacklist_data = [(bitem.identifier, bitem.bl_type, string_manipulation.truncate_string(bitem.additional_data, 20)) for bitem in blacklist_items]
    blacklist_table_lines = table2ascii(["Identifier", "Type", "Specific Data"], blacklist_data, alignments=[Alignment.LEFT, Alignment.LEFT, Alignment.LEFT]).split("\n")

    blacklist_pages = []
    while blacklist_table_lines:
      output_string, blacklist_table_lines = string_manipulation.add_string_until_length(blacklist_table_lines, 2000, "\n")
      embed = disnake.Embed(title="Blacklist", description=f"```\n{output_string}\n```", color=disnake.Color.orange())
      message_utils.add_author_footer(embed, inter.author)
      blacklist_pages.append(embed)

    embed_view = EmbedView(inter.author, blacklist_pages)
    await embed_view.run(inter)

  @blacklist_commands.sub_command(description=Strings.blacklist_report_cheater_description)
  @cooldowns.long_cooldown
  async def report_cheater(self, inter: disnake.CommandInteraction,
                           identifier: str=commands.Param(description=Strings.blacklist_report_identifier_param_description, autocomp=dt_identifier_autocomplete.autocomplete_identifier_guild_and_user),
                           reason: Optional[str]=commands.Param(default=None, description=Strings.blacklist_report_reason_param_description, max_length=3000)):
    await inter.response.defer(with_message=True, ephemeral=True)

    announce_channel = await object_getters.get_or_fetch_channel(self.bot, config.blacklist.report_channel_id)
    if announce_channel is None:
      return await message_utils.generate_error_message(inter, Strings.blacklist_report_report_channel_not_found)

    specifier = dt_identifier_autocomplete.identifier_to_specifier(identifier)
    if specifier is None:
      return await message_utils.generate_error_message(inter, Strings.dt_invalid_identifier)

    report_type, entity_id = specifier

    if report_type == "USER":
      user = dt_user_repo.get_dt_user(entity_id)
      if user is None:
        return await message_utils.generate_error_message(inter, Strings.blacklist_report_user_cheater_user_not_found)

      embed = disnake.Embed(title="User cheater report", color=disnake.Color.orange(), description=f"```\n{reason}\n```" if reason is not None else None)
      message_utils.add_author_footer(embed, inter.author)
      embed.add_field(name="Username", value=user.username)
      embed.add_field(name="ID", value=str(user.id))
      embed.add_field(name="Guild", value=f"{user.active_member.guild.name}" if user.active_member is not None else "None")
    elif report_type == "GUILD":
      guild = dt_guild_repo.get_dt_guild(entity_id)
      if guild is None:
        return await message_utils.generate_error_message(inter, Strings.blacklist_report_guild_cheater_guild_not_found)

      embed = disnake.Embed(title="Guild cheater report", color=disnake.Color.orange(), description=f"```\n{reason}\n```" if reason is not None else None)
      message_utils.add_author_footer(embed, inter.author)
      embed.add_field(name="Name", value=guild.name)
      embed.add_field(name="ID", value=str(guild.id))
    else:
      return await message_utils.generate_error_message(inter, Strings.blacklist_report_cheater_invalid_report_type)

    await announce_channel.send(embed=embed)
    await message_utils.generate_success_message(inter, Strings.blacklist_report_success)

def setup(bot):
  bot.add_cog(DTBlacklist(bot))
