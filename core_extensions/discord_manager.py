import asyncio
import disnake
from disnake.ext import commands

from features.base_cog import Base_Cog
from database import discord_objects_repo
from config import permissions, cooldowns
from config.strings import Strings
from utils import message_utils, string_manipulation
from utils.logger import setup_custom_logger

logger = setup_custom_logger(__name__)

class DiscordManager(Base_Cog):
  def __init__(self, bot):
    super(DiscordManager, self).__init__(bot, __file__)

    if self.bot.is_ready():
      loop = asyncio.get_event_loop()
      loop.create_task(self.pull_data_seq())

  @commands.Cog.listener()
  async def on_ready(self):
    await self.pull_data_seq()

  async def pull_data_seq(self):
    logger.info("Starting discord data pull")

    futures = [discord_objects_repo.get_or_create_discord_guild(g, commit=False) async for g in self.bot.fetch_guilds(limit=None)]
    await asyncio.gather(*futures)
    await discord_objects_repo.run_commit()

    for guild in self.bot.guilds:
      futures = [discord_objects_repo.get_or_create_discord_user(member, comit=False) for member in guild.members if not member.bot and not member.system]
      await asyncio.gather(*futures)
      await asyncio.sleep(0.001)
    await discord_objects_repo.run_commit()
    logger.info("Discord data pull finished")

  @commands.slash_command()
  async def discord_data_manager(self, inter: disnake.CommandInteraction):
    pass

  @discord_data_manager.sub_command(description=Strings.discord_manager_get_guilds_description)
  @permissions.bot_developer()
  async def get_guilds(self, inter: disnake.CommandInteraction):
    guild_strings = [f"{g.name} ({g.id})" for g in self.bot.guilds]
    while guild_strings:
      final_message, guild_strings = string_manipulation.add_string_until_length(guild_strings, 1900, "\n")
      await inter.send(Strings.discord_manager_get_guilds_message(message=final_message))

  @discord_data_manager.sub_command(description=Strings.discord_manager_pull_data_description)
  @commands.is_owner()
  @cooldowns.huge_cooldown
  async def pull_data(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)
    await self.pull_data_seq()
    await message_utils.generate_success_message(inter, Strings.discord_manager_pull_data_success)

  @commands.Cog.listener()
  async def on_guild_join(self, guild: disnake.Guild):
    await discord_objects_repo.get_or_create_discord_guild(guild)

    for member in guild.members:
      await discord_objects_repo.get_or_create_discord_user(member, comit=False)
    await discord_objects_repo.run_commit()

  @commands.Cog.listener()
  async def on_guild_remove(self, guild: disnake.Guild):
    await discord_objects_repo.remove_discord_guild(guild.id)

  @commands.Cog.listener()
  async def on_member_join(self, member: disnake.Member):
    await discord_objects_repo.get_or_create_discord_user(member)

  @commands.Cog.listener()
  async def on_member_remove(self, member: disnake.Member):
    await discord_objects_repo.remove_discord_user(member.id)

def setup(bot):
  bot.add_cog(DiscordManager(bot))
