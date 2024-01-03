# Error handling extension

import disnake
from disnake.ext import commands

from utils.logger import setup_custom_logger
from features.base_cog import Base_Cog
from features.base_bot import BaseAutoshardedBot

logger = setup_custom_logger(__name__)

class Errors(Base_Cog):
  def __init__(self, bot: BaseAutoshardedBot):
    super(Errors, self).__init__(bot, __file__)

  @commands.Cog.listener()
  async def on_command_error(self, ctx: commands.Context, error):
    await self.bot.error_logger.command_error_handling(ctx, error)

  @commands.Cog.listener()
  async def on_slash_command_error(self, inter: disnake.ApplicationCommandInteraction, error):
    await self.bot.error_logger.command_error_handling(inter, error)

  @commands.Cog.listener()
  async def on_user_command_error(self, inter: disnake.ApplicationCommandInteraction, error):
    await self.bot.error_logger.command_error_handling(inter, error)

  @commands.Cog.listener()
  async def on_message_command_error(self, inter: disnake.ApplicationCommandInteraction, error):
    await self.bot.error_logger.command_error_handling(inter, error)


def setup(bot):
  bot.add_cog(Errors(bot))
