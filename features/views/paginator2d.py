# Basic scroller for embeds
# Inspired by https://github.com/Toaster192/rubbergod/blob/master/buttons/embed.py

import disnake
from typing import List, Optional, Union

from utils import message_utils

def pagination_next(id: str, hor_page: int, vert_page: int, max_hor_page: int, max_vert_page: int, roll_around: bool = True):
  if 'next' in id:
    hor_page = 1
    next_vert_page = vert_page + 1
  elif 'prev' in id:
    hor_page = 1
    next_vert_page = vert_page - 1
  else:
    next_vert_page = vert_page

  if 'up' in id:
    next_hor_page = hor_page + 1
  elif 'down' in id:
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

  def __init__(self, author: disnake.User, embeds: List[List[disnake.Embed]], perma_lock: bool = False, roll_arroud: bool = True, timeout: Optional[float] = 300, invisible: bool=False, invert_list_dir: bool=False):
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

      if not perma_lock and not invisible:
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

        if not perma_lock and not invisible:
          # if permanent lock is applied, dynamic lock is removed from buttons
          self.lock_button = disnake.ui.Button(
            emoji="🔓",
            custom_id="embed:lock",
            style=disnake.ButtonStyle.success
          )
          self.add_item(self.lock_button)

  def embed(self):
    page = self.embeds[self.vert_page - 1][self.hor_page - 1]
    page.set_author(name=f"Page: {self.vert_page}/{self.max_vert_page} List: {self.hor_page}/{len(self.embeds[self.vert_page - 1])}")
    return page

  async def run(self, ctx):
    if isinstance(ctx, (disnake.ApplicationCommandInteraction, disnake.ModalInteraction, disnake.MessageCommandInteraction, disnake.CommandInteraction)):
      await ctx.send(embed=self.embed(), view=self, ephemeral=self.invisible)
      self.message = ctx
    else:
      self.message = await ctx.send(embed=self.embed(), view=self)

  async def interaction_check(self, interaction: disnake.MessageInteraction) -> None:
    if interaction.data.custom_id == "embed:lock":
      if interaction.author.id == self.author.id:
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

    if (self.perma_lock or self.locked) and interaction.author.id != self.author.id:
      await message_utils.generate_error_message(interaction, "You are not author of this embed")
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
      if isinstance(self.message, disnake.Message):
        await self.message.edit(view=self)
      else:
        await self.message.edit_original_message(view=self)
    except:
      pass
