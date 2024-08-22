import asyncio
import disnake
from disnake.ext import commands
from sqlalchemy import exc

from features.base_cog import Base_Cog
from database import discord_objects_repo, session_maker, run_commit_in_thread
from config import permissions, cooldowns, config
from config.strings import Strings
from utils import message_utils, string_manipulation
from utils.logger import setup_custom_logger
from utils import command_utils

logger = setup_custom_logger(__name__)

class DiscordManager(Base_Cog):
  def __init__(self, bot):
    super(DiscordManager, self).__init__(bot, __file__)

  def cog_load(self) -> None:
    if config.base.sync_discord:
      loop = asyncio.get_event_loop()
      loop.create_task(self.pull_data_loop())


  async def pull_data_seq(self):
    await self.bot.wait_until_ready()

    logger.info("Starting discord data pull")

    discord_guild_object_ids = []

    with session_maker() as session:
      async for guild in self.bot.fetch_guilds(limit=None):
        guild_object = await discord_objects_repo.get_or_create_discord_guild(session, guild)
        discord_guild_object_ids.append(guild_object.id)

        discord_member_object_ids = []
        async for member in guild.fetch_members(limit=None):
          await asyncio.sleep(0.05)
          if member.bot or member.system: continue

          member_object = await discord_objects_repo.get_or_create_discord_member(session, member, comit=False)
          discord_member_object_ids.append(member_object.user_id)

        await run_commit_in_thread(session)
        await discord_objects_repo.discord_member_cleanup(session, guild.id, discord_member_object_ids)
        await asyncio.sleep(1)

      await discord_objects_repo.discord_guild_cleanup(session, discord_guild_object_ids)
      await discord_objects_repo.discord_user_cleanup(session)

    logger.info("Discord data pull finished")

  async def pull_data_loop(self):
    while True:
      try:
        await self.pull_data_seq()
        break
      except exc.OperationalError as e:
        if e.connection_invalidated:
          logger.warning("Database connection failed, retrying later")
          await asyncio.sleep(60)
          logger.info("Retrying...")
        else:
          raise e

  @command_utils.master_only_slash_command(name="discord")
  async def discord_data_manager(self, inter: disnake.CommandInteraction):
    pass

  @discord_data_manager.sub_command(description=Strings.discord_manager_get_guilds_description)
  @permissions.bot_developer()
  @cooldowns.default_cooldown
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
  async def on_user_update(self, _, after: disnake.User):
    with session_maker() as session:
      await discord_objects_repo.get_or_create_discord_user(session, after)


  @commands.Cog.listener()
  async def on_guild_join(self, guild: disnake.Guild):
    with session_maker() as session:
      await discord_objects_repo.get_or_create_discord_guild(session, guild)

      for member in guild.members:
        if member.bot or member.system: continue
        await discord_objects_repo.get_or_create_discord_member(session, member, comit=False)

      await run_commit_in_thread(session)

  @commands.Cog.listener()
  async def on_guild_remove(self, guild: disnake.Guild):
    with session_maker() as session:
      await discord_objects_repo.remove_discord_guild(session, guild.id)

  @commands.Cog.listener()
  async def on_guild_update(self, _, after: disnake.Guild):
    with session_maker() as session:
      await discord_objects_repo.get_or_create_discord_guild(session, after)


  @commands.Cog.listener()
  async def on_member_join(self, member: disnake.Member):
    if member.bot or member.system: return

    with session_maker() as session:
      await discord_objects_repo.get_or_create_discord_member(session, member)

  @commands.Cog.listener()
  async def on_member_remove(self, member: disnake.Member):
    if member.bot or member.system: return

    with session_maker() as session:
      await discord_objects_repo.remove_discord_member(session, member.guild.id, member.id)

  @commands.Cog.listener()
  async def on_member_update(self, _, after: disnake.Member):
    if after.bot or after.system: return

    with session_maker() as session:
      await discord_objects_repo.get_or_create_discord_member(session, after)

def setup(bot):
  bot.add_cog(DiscordManager(bot))
