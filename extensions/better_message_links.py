import disnake
from disnake.ext import commands
import re

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from utils import object_getters, string_manipulation

logger = setup_custom_logger(__name__)

message_link_regex = re.compile(r"https://discord.com/channels/(\d*)/(\d*)/(\d*)")

class BetterMessageLinks(Base_Cog):
  def __init__(self, bot):
    super(BetterMessageLinks, self).__init__(bot, __file__)

  @commands.Cog.listener()
  async def on_message(self, message: disnake.Message):
    if message.author.bot or message.author.system or message.guild is None: return

    matches = message_link_regex.findall(message.content)
    for match in matches:
      if int(match[0]) != message.guild.id: continue

      original_message_channel = await object_getters.get_or_fetch_channel(message.guild, int(match[1]))
      if original_message_channel is None: continue

      original_message = await object_getters.get_or_fetch_message(self.bot, original_message_channel, int(match[2]))
      if original_message is None: continue

      embed = disnake.Embed(description=f"{string_manipulation.truncate_string(original_message.content, 3500) if original_message.content else '*No content*'}\n\n**Source**\n[Jump to message]({original_message.jump_url}) in {original_message.channel.mention}", color=disnake.Color.dark_grey())
      embed.set_author(name=f"{original_message.author.display_name} said:", icon_url=original_message.author.display_avatar.url)
      embed.timestamp = original_message.created_at
      await message.reply(embed=embed)

def setup(bot):
  bot.add_cog(BetterMessageLinks(bot))
