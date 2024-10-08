import disnake
from disnake.ext import commands

from config import permissions, cooldowns
from config.strings import Strings
from features.base_cog import Base_Cog
from database import discord_objects_repo, session_maker
from utils import message_utils

class Settings(Base_Cog):
  def __init__(self, bot):
    super(Settings, self).__init__(bot, __file__)

  @commands.slash_command(name="settings", dm_permission=False)
  async def settings_commands(self, inter: disnake.CommandInteraction):
    pass

  @settings_commands.sub_command_group(name="admin_role")
  @permissions.guild_administrator()
  @cooldowns.default_cooldown
  async def admin_role_commands(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

  @admin_role_commands.sub_command(name="set", description=Strings.settings_admin_role_set_description)
  async def admin_role_set(self, inter: disnake.CommandInteraction,
                           admin_role: disnake.Role=commands.Param(description=Strings.settings_admin_role_set_admin_role_param_description)):
    if admin_role is not None and hasattr(admin_role, "id"):
      with session_maker() as session:
        guild = await discord_objects_repo.get_or_create_discord_guild(session, inter.guild)
        guild.admin_role_id = str(admin_role.id)

      return await message_utils.generate_success_message(inter, Strings.settings_admin_role_set_success(admin_role=admin_role.mention))
    await message_utils.generate_error_message(inter, Strings.settings_admin_role_set_failed)

  @admin_role_commands.sub_command(name="remove", description=Strings.settings_admin_role_remove_description)
  async def admin_role_remove(self, inter: disnake.CommandInteraction):
    with session_maker() as session:
      guild = await discord_objects_repo.get_or_create_discord_guild(session, inter.guild)
      if guild.admin_role_id is not None:
        guild.admin_role_id = None

        return await message_utils.generate_success_message(inter, Strings.settings_admin_role_remove_success)
    await message_utils.generate_error_message(inter, Strings.settings_admin_role_remove_failed)

def setup(bot):
  bot.add_cog(Settings(bot))
