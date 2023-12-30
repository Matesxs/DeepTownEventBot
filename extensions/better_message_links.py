import disnake
from disnake.ext import commands
import re

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from utils import object_getters, string_manipulation
from database import discord_objects_repo
from config import permissions, cooldowns
from config.strings import Strings
from utils import message_utils

logger = setup_custom_logger(__name__)

message_link_regex = re.compile(r"https://discord.com/channels/(\d*)/(\d*)/(\d*)")

class BetterMessageLinks(Base_Cog):
  def __init__(self, bot):
    super(BetterMessageLinks, self).__init__(bot, __file__)

  @commands.Cog.listener()
  async def on_message(self, message: disnake.Message):
    if message.author.bot or message.author.system or message.guild is None:
      # logger.info("Invalid message author or not in guild")
      return

    if not (await discord_objects_repo.better_message_links_enabled(message.guild.id)):
      return

    destination_channel_permissions = message.channel.permissions_for(message.guild.me)
    if not destination_channel_permissions.send_messages or not destination_channel_permissions.attach_files:
      return

    matches = message_link_regex.findall(message.content)
    for match in matches:
      if int(match[0]) != message.guild.id:
        # logger.info(f"Message `{message.id}` is from another server")
        continue

      original_message_channel = await object_getters.get_or_fetch_channel(message.guild, int(match[1]))
      if original_message_channel is None:
        # logger.info(f"Failed to get channel `{match[1]}` from link in `{message.id}`")
        continue

      source_channel_permissions = original_message_channel.permissions_for(message.guild.me)
      if not source_channel_permissions.read_messages or not source_channel_permissions.read_message_history:
        # logger.info(f"Invalid read permissions for channel `{match[1]}` from link in `{message.id}`")
        continue

      original_message = await object_getters.get_or_fetch_message(self.bot, original_message_channel, int(match[2]))
      if original_message is None:
        # logger.info(f"Failed to get message `{match[2]}` from link in `{message.id}`")
        continue

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

  @commands.slash_command(name="better_message_links")
  @permissions.guild_administrator_role()
  @cooldowns.default_cooldown
  async def better_message_links_commands(self, inter: disnake.CommandInteraction):
    pass

  @better_message_links_commands.sub_command(name="enable", description=Strings.settings_better_message_links_enable_description)
  async def better_message_links_enable(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    guild = await discord_objects_repo.get_or_create_discord_guild(inter.guild)
    guild.enable_better_message_links = True
    await discord_objects_repo.run_commit()

    await message_utils.generate_success_message(inter, Strings.settings_better_message_links_enable_success)

  @better_message_links_commands.sub_command(name="disable", description=Strings.settings_better_message_links_disable_description)
  async def better_message_links_disable(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    guild = await discord_objects_repo.get_or_create_discord_guild(inter.guild)
    guild.enable_better_message_links = False
    await discord_objects_repo.run_commit()

    await message_utils.generate_success_message(inter, Strings.settings_better_message_links_disabled_success)

def setup(bot):
  bot.add_cog(BetterMessageLinks(bot))
