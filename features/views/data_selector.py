import disnake
from typing import List, Optional

from utils import message_utils

class DataSelectorDropdown(disnake.ui.Select):
  def __init__(self, author: disnake.User, not_selected: List[str], selected: List[str], min_selected: int=1, max_selected: Optional[int]=None):
    all_options_number = len(not_selected) + len(selected)

    assert all_options_number <= 25, "Too much data to select"

    self.author = author

    if max_selected is None:
      max_selected = all_options_number
    if min_selected > all_options_number:
      min_selected = all_options_number
    if max_selected < min_selected:
      max_selected = min_selected

    options = []
    for item in selected:
      options.append(disnake.SelectOption(label=item, default=True))
    for item in not_selected:
      options.append(disnake.SelectOption(label=item, default=False))

    super(DataSelectorDropdown, self).__init__(min_values=min_selected, max_values=max_selected, options=options)

  async def callback(self, inter: disnake.MessageInteraction):
    await inter.response.defer()

    if inter.author.id != self.author.id:
      return await message_utils.generate_error_message(inter, "You are not author of this settings")

class DataSelector(disnake.ui.View):
  def __init__(self, author: disnake.User, not_selected: List[str], selected: List[str], min_selected: int=1, max_selected: Optional[int]=None, invisible: bool=False):
    super(DataSelector, self).__init__(timeout=600)

    self.author = author
    self.message = None
    self.available_colms = not_selected + selected
    self.invisible = invisible

    self.result = selected

    self.selector = DataSelectorDropdown(author, not_selected, selected, min_selected, max_selected)
    self.add_item(self.selector)

  async def run(self, ctx):
    if isinstance(ctx, (disnake.ApplicationCommandInteraction, disnake.ModalInteraction, disnake.MessageCommandInteraction, disnake.CommandInteraction)):
      await ctx.send(view=self, ephemeral=self.invisible)
      self.message = await ctx.original_message()
    else:
      self.message = await ctx.send(view=self)

  def get_results(self):
    return [colm for colm in self.available_colms if colm in self.result]

  @disnake.ui.button(style=disnake.ButtonStyle.green, label="Generate")
  async def generate_button(self, button: disnake.ui.Button, inter: disnake.MessageInteraction):
    if self.selector.values is not None and self.selector.values:
      self.result = self.selector.values

    button.disabled = True
    self.selector.disabled = True

    await inter.response.edit_message(view=self)
    self.stop()

  async def interaction_check(self, interaction: disnake.MessageInteraction) -> bool:
    if interaction.author.id == self.author.id:
      return True

    await message_utils.generate_error_message(interaction, "You are not author of this settings")
    return False

  async def on_timeout(self) -> None:
    try:
      await self.message.delete()
    except:
      pass
  