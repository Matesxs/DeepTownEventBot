import disnake

from features.views.pool_prompt import PoolView

class PoolModal(disnake.ui.Modal):
  def __init__(self, author: disnake.User, pool_duration_seconds: int):
    components = [
      disnake.ui.TextInput(label="Description", custom_id="vote_setup:description", required=False, max_length=3000, placeholder="Optional description", style=disnake.TextInputStyle.multi_line),
      disnake.ui.TextInput(label="Choice 1", custom_id="vote_setup:choice_1", required=True, max_length=300, placeholder="Required choice 1"),
      disnake.ui.TextInput(label="Choice 2", custom_id="vote_setup:choice_2", required=True, max_length=300, placeholder="Required choice 2"),
      disnake.ui.TextInput(label="Choice 3", custom_id="vote_setup:choice_3", required=False, max_length=300, placeholder="Optional choice 3"),
      disnake.ui.TextInput(label="Choice 4", custom_id="vote_setup:choice_4", required=False, max_length=300, placeholder="Optional choice 4")
    ]
    super(PoolModal, self).__init__(title="Setup Pool", custom_id="vote_setup", timeout=300, components=components)
    self.pool_duration = pool_duration_seconds
    self.author = author

  async def callback(self, interaction: disnake.ModalInteraction) -> None:
    choices = [choice for (key, choice) in dict(interaction.text_values).items() if "choice" in key and choice != ""]
    vote_prompt = PoolView(author=self.author, duration_seconds=self.pool_duration, description=interaction.text_values["vote_setup:description"], choices=choices)
    await vote_prompt.run(interaction)
