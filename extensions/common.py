import disnake
from disnake.ext import commands
import datetime
import time
import humanize

from config import cooldowns, Strings, config
from features.base_cog import Base_Cog
from utils import message_utils

class Common(Base_Cog):
  def __init__(self, bot):
    super(Common, self).__init__(bot, __file__)

  @commands.slash_command(name="common")
  async def common_commands(self, inter: disnake.CommandInteraction):
    pass

  @common_commands.sub_command(description=Strings.common_uptime_description)
  @cooldowns.default_cooldown
  async def uptime(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)
    description = f"{humanize.naturaldelta(datetime.datetime.now(datetime.UTC) - self.bot.start_time)}\nLast error: {humanize.naturaltime(datetime.datetime.now(datetime.UTC) - self.bot.last_error) if self.bot.last_error is not None else 'Never'}"
    embed = disnake.Embed(title="Uptime", description=description, color=disnake.Color.dark_blue())
    message_utils.add_author_footer(embed, inter.author)
    await inter.send(embed=embed)

  @common_commands.sub_command(description=Strings.common_ping_description)
  @cooldowns.default_cooldown
  async def ping(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    em = disnake.Embed(color=disnake.Color.dark_blue(), title="Pong!")
    message_utils.add_author_footer(em, inter.author)

    start_time = time.time()
    await inter.send(embed=em)
    end_time = time.time()

    em.description = f'Bot: {round(self.bot.latency * 1000)} ms\nAPI: {round((end_time - start_time) * 1000)}ms'
    await inter.edit_original_response(embed=em)

  @common_commands.sub_command(name="invite", description=Strings.common_invite_description)
  @cooldowns.default_cooldown
  async def invite_link(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    link = f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&scope=bot&permissions={config.base.required_permissions}"
    embed = disnake.Embed(title=self.bot.user.display_name, description=f"[Invite link]({link})", color=disnake.Color.dark_blue())
    embed.set_thumbnail(self.bot.user.avatar.url)
    message_utils.add_author_footer(embed, inter.author)

    await inter.send(embed=embed)

def setup(bot):
  bot.add_cog(Common(bot))
