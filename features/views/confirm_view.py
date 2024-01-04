import disnake
import datetime

from utils import message_utils, string_manipulation

class ConfirmView(disnake.ui.View):
  def __init__(self, ctx, text: str, invisible: bool = False, timeout: int = 600):
    super(ConfirmView, self).__init__(timeout=timeout)
    self.ctx = ctx
    self.message = None
    self.invisible = invisible
    self.text = text
    self.cstm_timeout = timeout

    self.result = False

  async def run(self):
    if self.ctx is None:
      return False

    timeout_timestamp = int((datetime.datetime.now() + datetime.timedelta(seconds=self.cstm_timeout)).timestamp())
    prompt_embed = disnake.Embed(title="Confirmation prompt", description=string_manipulation.truncate_string(self.text, 3000) + f"\n\nClosing <t:{timeout_timestamp}:R> (<t:{timeout_timestamp}:T>) and will be rejected", color=disnake.Color.dark_blue())
    message_utils.add_author_footer(prompt_embed, self.ctx.author)

    try:
      if isinstance(self.ctx, (disnake.ApplicationCommandInteraction, disnake.ModalInteraction, disnake.MessageCommandInteraction, disnake.CommandInteraction)):
        await self.ctx.send(embed=prompt_embed, view=self, ephemeral=self.invisible)
        self.message = await self.ctx.original_message()
      else:
        self.message = await self.ctx.reply(embed=prompt_embed, view=self)
    except:
      return False

    return True

  @disnake.ui.button(style=disnake.ButtonStyle.green, label="Confirm")
  async def confirm_button(self, _, __):
    self.result = True
    await self.on_timeout()
    self.stop()
    return True

  @disnake.ui.button(style=disnake.ButtonStyle.red, label="Reject")
  async def reject_button(self, _, __):
    await self.on_timeout()
    self.stop()
    return True

  def get_result(self):
    return self.result

  async def interaction_check(self, interaction: disnake.MessageInteraction) -> bool:
    if interaction.author.id == self.ctx.author.id:
      return True

    await message_utils.generate_error_message(interaction, "You are not author of this prompt")
    return False

  async def on_timeout(self) -> None:
    try:
      await self.message.delete()
      self.message = None
    except:
      pass
