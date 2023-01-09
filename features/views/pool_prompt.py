import datetime
import disnake
from typing import List, Optional, Union

from utils import string_manipulation, message_utils

reaction_ids = ["vote:zero", "vote:one", "vote:two", "vote:three", "vote:four", "vote:six", "vote:seven", "vote:eight", "vote:nine"]
reactions = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣"]
reaction_buttons = [disnake.ui.Button(emoji=f"{reactions[i]}", custom_id=rid,style=disnake.ButtonStyle.primary) for i, rid in enumerate(reaction_ids)]

class PoolView(disnake.ui.View):
  def __init__(self, author: disnake.User, description: str, choices: List[str], duration_seconds: int, color: disnake.Color=disnake.Color.dark_blue()):
    super(PoolView, self).__init__(timeout=duration_seconds)

    self.message: Optional[Union[disnake.Message, disnake.ApplicationCommandInteraction, disnake.ModalInteraction, disnake.MessageCommandInteraction]] = None
    self.choices = choices
    self.description = description
    self.color = color
    self.duration_seconds = duration_seconds
    self.author = author

    self.number_of_choices = min(len(choices), 10)
    self.results = [0 for _ in range(self.number_of_choices)]
    self.participants = []

    for i in range(self.number_of_choices):
      self.add_item(reaction_buttons[i])

  def generate_embed(self):
    embed = disnake.Embed(title="Pool", description=string_manipulation.truncate_string(self.description, 4000), color=self.color)
    for idx, (reaction_id, choice) in enumerate(zip(reaction_ids, self.choices)):
      embed.add_field(name=f"{reactions[idx]}: {self.results[idx]}", value=string_manipulation.truncate_string(choice, 1000))

    embed.set_author(name=self.author.display_name, icon_url=self.author.display_avatar.url)
    embed.set_footer(text=f"Ending at {datetime.datetime.utcnow() + datetime.timedelta(seconds=self.duration_seconds)} UTC")
    return embed
  async def run(self, ctx):
    if self.number_of_choices == 0:
      return None

    embed = self.generate_embed()
    message = await ctx.send(embed=embed, view=self)
    if isinstance(ctx, (disnake.ApplicationCommandInteraction, disnake.ModalInteraction, disnake.MessageCommandInteraction)):
      self.message = await ctx.original_message()
    else:
      self.message = message

  async def interaction_check(self, interaction: disnake.MessageInteraction):
    if interaction.author.id in self.participants:
      await message_utils.generate_error_message(interaction, "You already participated in this pool")
      return False

    self.participants.append(interaction.author.id)

    if interaction.data.custom_id not in reaction_ids:
      self.participants.remove(interaction.author.id)
      return

    try:
      inter_index = reaction_ids.index(interaction.data.custom_id)
    except:
      self.participants.remove(interaction.author.id)
      return False

    self.results[inter_index] += 1
    await message_utils.generate_success_message(interaction, f"You voted for choice {reactions[inter_index]}\n`{self.choices[inter_index]}`")

    embed = self.generate_embed()
    try:
      await self.message.edit(embed=embed)
    except:
      pass
    return True

  async def stop(self) -> None:
    super(PoolView, self).stop()
    await self.on_timeout()

  async def on_timeout(self):
    try:
      self.clear_items()
      await self.message.edit(view=self)
    except:
      pass

    max_res = max(self.results)

    if max_res == 0:
      embed = disnake.Embed(title="Pool results", description=f"There is no winner", color=disnake.Color.orange())
    else:
      res_indexes = []
      for idx, result in enumerate(self.results):
        if result == max_res:
          res_indexes.append(idx)

      res_reactions = [reaction for idx, reaction in enumerate(reactions) if idx in res_indexes]
      res_choices, _ = string_manipulation.add_string_until_length([choice for idx, choice in enumerate(self.choices) if idx in res_indexes], 3000, "\n")
      embed = disnake.Embed(title="Pool results", description=f"{', '.join(res_reactions)} {'choice' if len(res_indexes) == 1 else 'choices'} won:\n`{res_choices}`\n[Link]({self.message.jump_url})", color=self.color)

    try:
      await self.message.reply(embed=embed)
    except:
      pass