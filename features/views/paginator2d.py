# Basic scroller for embeds
# Inspired by https://github.com/Toaster192/rubbergod/blob/master/buttons/embed.py

import disnake
from typing import List, Optional, Union

from config import permissions
from utils import message_utils

def pagination_next(bid: str, hor_page: int, vert_page: int, max_hor_page: int, max_vert_page: int, roll_around: bool = True):
  if 'next' in bid:
    hor_page = 1
    next_vert_page = vert_page + 1
  elif 'prev' in bid:
    hor_page = 1
    next_vert_page = vert_page - 1
  else:
    next_vert_page = vert_page

  if 'up' in bid:
    next_hor_page = hor_page + 1
  elif 'down' in bid:
    next_hor_page = hor_page - 1
  else:
    next_hor_page = hor_page

  if roll_around and next_vert_page == 0:
    next_vert_page = max_vert_page
  elif roll_around and next_vert_page > max_vert_page:
    next_vert_page = 1

  if roll_around and next_hor_page == 0:
    next_hor_page = max_hor_page
  elif roll_around and next_hor_page > max_hor_page:
    next_hor_page = 1

  return next_vert_page, next_hor_page

reaction_ids = ["embed:prev_page", "embed:up_page", "embed:next_page", "embed:down_page"]

class EmbedView2D(disnake.ui.View):

  def __init__(self, author: disnake.User, embeds: List[List[disnake.Embed]], can_lock: bool = True, perma_lock: bool = False, roll_arroud: bool = True, timeout: Optional[float] = 600, invisible: bool=False, invert_list_dir: bool=False, delete_on_timeout: bool=False):
    self.message: Optional[Union[disnake.Message, disnake.ApplicationCommandInteraction, disnake.ModalInteraction, disnake.MessageCommandInteraction]] = None
    self.vert_page = 1
    self.hor_page = 1

    self.author = author
    self.locked = False
    self.roll_arroud = roll_arroud
    self.perma_lock = perma_lock
    self.embeds = embeds
    self.max_vert_page = len(embeds)
    self.invisible = invisible
    self.delete_on_timeout = delete_on_timeout
    super().__init__(timeout=timeout)

    if self.max_vert_page > 1:
      self.add_item(
        disnake.ui.Button(
          emoji="◀",
          custom_id="embed:prev_page",
          style=disnake.ButtonStyle.primary
        )
      )
      self.add_item(
        disnake.ui.Button(
          emoji="🔼",
          custom_id="embed:up_page" if not invert_list_dir else "embed:down_page",
          style=disnake.ButtonStyle.primary
        )
      )
      self.add_item(
        disnake.ui.Button(
          emoji="🔽",
          custom_id="embed:down_page" if not invert_list_dir else "embed:up_page",
          style=disnake.ButtonStyle.primary
        )
      )
      self.add_item(
        disnake.ui.Button(
          emoji="▶",
          custom_id="embed:next_page",
          style=disnake.ButtonStyle.primary
        )
      )

      if not perma_lock and not invisible and can_lock:
        # if permanent lock is applied, dynamic lock is removed from buttons
        self.lock_button = disnake.ui.Button(
          emoji="🔓",
          custom_id="embed:lock",
          style=disnake.ButtonStyle.success
        )
        self.add_item(self.lock_button)
    else:
      if len(embeds[0]) > 0:
        self.add_item(
          disnake.ui.Button(
            emoji="🔼",
            custom_id="embed:up_page" if not invert_list_dir else "embed:down_page",
            style=disnake.ButtonStyle.primary
          )
        )
        self.add_item(
          disnake.ui.Button(
            emoji="🔽",
            custom_id="embed:down_page" if not invert_list_dir else "embed:up_page",
            style=disnake.ButtonStyle.primary
          )
        )

        if not perma_lock and not invisible and can_lock:
          # if permanent lock is applied, dynamic lock is removed from buttons
          self.lock_button = disnake.ui.Button(
            emoji="🔓",
            custom_id="embed:lock",
            style=disnake.ButtonStyle.success
          )
          self.add_item(self.lock_button)

    self.add_item(disnake.ui.Button(emoji="🗑️", style=disnake.ButtonStyle.red, custom_id="embed:trash"))

  def embed(self):
    page = self.embeds[self.vert_page - 1][self.hor_page - 1]
    page.set_author(name=f"Page: {self.vert_page}/{self.max_vert_page} List: {self.hor_page}/{len(self.embeds[self.vert_page - 1])}")
    return page

  async def run(self, ctx):
    if isinstance(ctx, (disnake.ApplicationCommandInteraction, disnake.ModalInteraction)):
      await ctx.send(embed=self.embed(), view=self, ephemeral=self.invisible)
      self.message = await ctx.original_response()
    else:
      self.message = await ctx.reply(embed=self.embed(), view=self)

  async def interaction_check(self, interaction: disnake.MessageInteraction) -> None:
    if interaction.data.custom_id == "embed:lock":
      if interaction.author.id == self.author.id or (await permissions.is_bot_developer(interaction)):
        self.locked = not self.locked
        if self.locked:
          self.lock_button.style = disnake.ButtonStyle.danger
          self.lock_button.emoji = "🔒"
        else:
          self.lock_button.style = disnake.ButtonStyle.success
          self.lock_button.emoji = "🔓"
        await interaction.response.edit_message(view=self)
      else:
        await message_utils.generate_error_message(interaction, "You are not author of this embed")
      return

    if interaction.data.custom_id == "embed:trash":
      if interaction.author.id == self.author.id or (await permissions.has_guild_administrator_role(interaction)):
        self.delete_on_timeout = True
        await self.on_timeout()
      else:
        await message_utils.generate_error_message(interaction, "You are not author of this embed")
      return

    if (self.perma_lock or self.locked) and interaction.author.id != self.author.id and (not await permissions.has_guild_administrator_role(interaction)):
      await message_utils.generate_error_message(interaction, "You are not author of this embed")
      return

    if interaction.data.custom_id not in reaction_ids:
      return

    self.vert_page, self.hor_page = pagination_next(
      interaction.data.custom_id,
      self.hor_page,
      self.vert_page,
      len(self.embeds[self.vert_page - 1]),
      self.max_vert_page,
      self.roll_arroud
    )
    await interaction.response.edit_message(embed=self.embed())

  async def on_timeout(self):
    try:
      self.clear_items()
      if self.message is not None:
        if self.delete_on_timeout:
          await self.message.delete()
        else:
          self.add_item(message_utils.get_delete_button(self.author))
          await self.message.edit(view=self)
    except:
      pass
