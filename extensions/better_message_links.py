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

      attachments = [a for a in original_message.attachments if a.size <= 8_000_000]
      image_attachment = None
      other_files = []
      for attachment in attachments:
        if attachment.content_type is not None:
          if attachment.content_type.startswith("image") and image_attachment is None: # First image is set as image of embed, rest will be sent as files
            image_attachment = attachment
          else:
            other_files.append(await attachment.to_file())
        else:
          other_files.append(await attachment.to_file())

      repost_embed = disnake.Embed(description=f"{string_manipulation.truncate_string(original_message.content, 3500) if original_message.content else '*No content*'}\n\n**Source**\n[Jump to message]({original_message.jump_url}) in {original_message.channel.mention}", color=disnake.Color.dark_grey())
      repost_embed.set_author(name=f"{original_message.author.display_name} said:", icon_url=original_message.author.display_avatar.url)
      if image_attachment is not None:
        repost_embed.set_image(url=image_attachment.url)
      repost_embed.timestamp = original_message.created_at

      repost_message = await message.reply(embed=repost_embed)
      if original_message.embeds:
        await repost_message.reply(embeds=original_message.embeds) # If original message had embeds then send them as separated message

      if other_files:
        await repost_message.reply(files=other_files) # To separate files under the first better repost message

def setup(bot):
  bot.add_cog(BetterMessageLinks(bot))
