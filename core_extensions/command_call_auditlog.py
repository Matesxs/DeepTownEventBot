import disnake
from disnake.ext import commands, tasks
import asyncio

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from utils import command_utils
import database
from database.tables import command_call_auditlog
from database import discord_objects_repo

logger = setup_custom_logger(__name__)

class CommandCallAuditlog(Base_Cog):
  def __init__(self, bot):
    super(CommandCallAuditlog, self).__init__(bot, __file__)

    self.data_queue = asyncio.Queue(maxsize=200)

  def cog_load(self) -> None:
    if not self.command_processing_task.is_running():
      self.command_processing_task.start()

  def cog_unload(self) -> None:
    if self.command_processing_task.is_running():
      self.command_processing_task.cancel()

  @commands.Cog.listener()
  async def on_slash_command_completion(self, inter: disnake.ApplicationCommandInteraction):
    await self.data_queue.put((inter, False))

  @commands.Cog.listener()
  async def on_slash_command_error(self, inter: disnake.ApplicationCommandInteraction, _):
    await self.data_queue.put((inter, True))


  @commands.Cog.listener()
  async def on_user_command_completion(self, inter: disnake.ApplicationCommandInteraction):
    await self.data_queue.put((inter, False))

  @commands.Cog.listener()
  async def on_user_command_error(self, inter: disnake.ApplicationCommandInteraction, _):
    await self.data_queue.put((inter, True))


  @commands.Cog.listener()
  async def on_message_command_completion(self, inter: disnake.ApplicationCommandInteraction):
    await self.data_queue.put((inter, False))

  @commands.Cog.listener()
  async def on_message_command_error(self, inter: disnake.ApplicationCommandInteraction, _):
    await self.data_queue.put((inter, True))


  @tasks.loop(seconds=10)
  async def command_processing_task(self):
    if self.data_queue.empty():
      return

    while not self.data_queue.empty():
      item = await self.data_queue.get()
      if item[0].author.bot or item[0].author.system: continue

      context = await command_utils.parse_context(item[0])

      if "system logout" in context["command"] or "system update" in context["command"]:
        continue

      guild = context["guild"]
      if guild is not None:
        await discord_objects_repo.get_or_create_discord_guild(context["guild"])

        member = disnake.utils.get(guild.members, id=context["author"].id)
        if member is not None:
          await discord_objects_repo.get_or_create_discord_member(member)
        else:
          await discord_objects_repo.get_or_create_discord_user(context["author"])
      else:
        await discord_objects_repo.get_or_create_discord_user(context["author"])

      await command_call_auditlog.CommandCallAuditlog.create_from_context(context, item[1])

    await database.run_commit()


def setup(bot):
  bot.add_cog(CommandCallAuditlog(bot))
