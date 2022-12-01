import disnake
from typing import List, Optional

from utils import message_utils

class DataSelector(disnake.ui.View):
  def __init__(self, author: disnake.User, data_options: List[str], default_selected_options: List[str], min_selected: int=1, max_selected: Optional[int]=None, invisible: bool=False):
    super(DataSelector, self).__init__(timeout=600)

    assert len(data_options) <= 25, "Too much data to select"

    if max_selected is None:
      max_selected = len(data_options)
    if min_selected > len(data_options):
      min_selected = len(data_options)
    if max_selected < min_selected:
      max_selected = min_selected

    self.author = author
    self.message = None
    self.available_colms = data_options
    self.invisible = invisible

    self.result = default_selected_options

    options = []
    for col in data_options:
      options.append(disnake.SelectOption(label=col, default=col in default_selected_options))

    self.selector = disnake.ui.StringSelect(min_values=min_selected, max_values=max_selected, options=options, custom_id="data_selector:selector")
    self.add_item(self.selector)
    self.add_item(disnake.ui.Button(style=disnake.ButtonStyle.green, label="Generate", custom_id="data_selector:generate_button"))

  async def run(self, ctx):
    if isinstance(ctx, (disnake.ApplicationCommandInteraction, disnake.ModalInteraction, disnake.MessageCommandInteraction, disnake.CommandInteraction)):
      await ctx.send(view=self, ephemeral=self.invisible)
      self.message = await ctx.original_message()
    else:
      self.message = await ctx.send(view=self)

  def get_results(self):
    return [colm for colm in self.available_colms if colm in self.result]

  async def interaction_check(self, interaction: disnake.MessageInteraction) -> bool:
    if interaction.author.id == self.author.id:
      if interaction.data.custom_id == "data_selector:generate_button":
        if self.selector.values is not None and self.selector.values:
          self.result = self.selector.values
        self.stop()

        if self.message is not None:
          await self.message.delete()
      else:
        self.selector.refresh_state(interaction)
        await interaction.send("`Selected data updated`", ephemeral=True, delete_after=5)
      return True

    await message_utils.generate_error_message(interaction, "You are not author of this settings")
    return False

  async def on_timeout(self) -> None:
    try:
      await self.message.delete()
    except:
      pass
  