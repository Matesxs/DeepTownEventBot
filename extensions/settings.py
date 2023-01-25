import disnake
from disnake.ext import commands

from config import permissions, cooldowns
from config.strings import Strings
from features.base_cog import Base_Cog
from database import discord_objects_repo
from utils import message_utils

class Settings(Base_Cog):
  def __init__(self, bot):
    super(Settings, self).__init__(bot, __file__)

  @commands.slash_command(name="settings")
  async def settings_commands(self, inter: disnake.CommandInteraction):
    pass

  @settings_commands.sub_command_group(name="admin_role")
  @permissions.guild_owner()
  @cooldowns.default_cooldown
  @commands.guild_only()
  async def admin_role_commands(self, inter: disnake.CommandInteraction):
    pass

  @admin_role_commands.sub_command(name="set", description=Strings.settings_admin_role_set_description)
  async def admin_role_set(self, inter: disnake.CommandInteraction,
                           admin_role: disnake.Role=commands.Param(description=Strings.settings_admin_role_set_admin_role_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    if admin_role is not None and hasattr(admin_role, "id"):
      guild = await discord_objects_repo.get_or_create_discord_guild(inter.guild)
      guild.admin_role_id = str(admin_role.id)
      await discord_objects_repo.run_commit()

      return await message_utils.generate_success_message(inter, Strings.settings_admin_role_set_success(admin_role=admin_role.mention))
    await message_utils.generate_error_message(inter, Strings.settings_admin_role_set_failed)

  @admin_role_commands.sub_command(name="remove", description=Strings.settings_admin_role_remove_description)
  async def admin_role_remove(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    guild = await discord_objects_repo.get_or_create_discord_guild(inter.guild)
    if guild.admin_role_id is not None:
      guild.admin_role_id = None
      await discord_objects_repo.run_commit()

      return await message_utils.generate_success_message(inter, Strings.settings_admin_role_remove_success)
    await message_utils.generate_error_message(inter, Strings.settings_admin_role_remove_failed)

def setup(bot):
  bot.add_cog(Settings(bot))
