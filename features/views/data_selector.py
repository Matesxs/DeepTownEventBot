import disnake
from typing import List

from utils import message_utils

class DataSelector(disnake.ui.View):
  def __init__(self, author: disnake.User, available_colms: List[str], default_enabled_colms: List[str]):
    super(DataSelector, self).__init__()

    self.author = author
    self.message = None
    self.available_colms = available_colms

    self.result = default_enabled_colms

    options = []
    for col in available_colms:
      options.append(disnake.SelectOption(label=col, default=col in default_enabled_colms))

    self.selector = disnake.ui.StringSelect(min_values=1, max_values=len(available_colms), options=options, custom_id="data_selector")
    self.add_item(self.selector)
    self.add_item(disnake.ui.Button(style=disnake.ButtonStyle.green, label="Generate", custom_id="data_selector_generate_button"))

  def get_results(self):
    return [colm for colm in self.available_colms if colm in self.result]

  async def interaction_check(self, interaction: disnake.MessageInteraction) -> bool:
    if interaction.author.id == self.author.id:
      if interaction.data.custom_id == "data_selector_generate_button":
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
  