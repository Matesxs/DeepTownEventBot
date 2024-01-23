import disnake
from disnake.ext import commands
from typing import List
import asyncio
import traceback

from config import permissions
from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from utils import object_getters, message_utils

logger = setup_custom_logger(__name__)

class Listeners(Base_Cog):
  def __init__(self, bot):
    super(Listeners, self).__init__(bot, __file__)

  @commands.Cog.listener()
  async def on_button_click(self, inter: disnake.MessageInteraction):
    if not isinstance(inter.component, disnake.Button): return
    if inter.author.bot or inter.author.system: return

    button_custom_id = inter.component.custom_id

    if button_custom_id is not None:
      splits = button_custom_id.split(":")
      command = splits[0]

      if command == "msg_delete":
        if inter.message.author.id == self.bot.user.id:
          if not (len(splits) >= 2 and int(splits[1]) == inter.author.id) or (await permissions.has_guild_administrator_role(inter)):
            return await message_utils.generate_error_message(inter, "You are not allowed to delete this message")

          messages = [inter.message]
          message_reference = inter.message.reference
          while message_reference is not None:
            message = await object_getters.get_or_fetch_message(self.bot, inter.message.channel, message_reference.message_id)
            if messages is not None:
              if message.author.id == self.bot.user.id:
                messages.append(message)

          for message in messages:
            await message_utils.delete_message(self.bot, message)
            await asyncio.sleep(0.05)

          await message_utils.generate_success_message(inter, f"`{len(messages)}` messages deleted")

  @commands.Cog.listener()
  async def on_raw_message_edit(self, payload: disnake.RawMessageUpdateEvent):
    before = payload.cached_message
    after = self.bot.get_message(payload.message_id)

    if after is None:
      channel = self.bot.get_channel(payload.channel_id)

      if channel is None:
        try:
          channel = await self.bot.fetch_channel(payload.channel_id)
        except:
          return

      try:
        after = await channel.fetch_message(payload.message_id)
      except:
        return

      if after is None:
        return

    cogs: List[Base_Cog] = self.bot.cogs.values()
    try:
      cogs_listening_futures = [cog.handle_message_edited(before, after) for cog in cogs]
      await asyncio.gather(*cogs_listening_futures)
    except:
      logger.warning(f"Failed to execute message edit handler\n{traceback.format_exc()}")

def setup(bot):
  bot.add_cog(Listeners(bot))
