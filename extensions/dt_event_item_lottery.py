import disnake
from disnake.ext import commands

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger

logger = setup_custom_logger(__name__)

class DTEventItemLottery(Base_Cog):
  def __init__(self, bot):
    super(DTEventItemLottery, self).__init__(bot, __file__)

  @commands.Cog.listener()
  async def on_button_click(self, inter: disnake.MessageInteraction):
    if not isinstance(inter.component, disnake.ui.Button): return

    button_custom_id = inter.component.custom_id
    if button_custom_id is None or not button_custom_id.startswith("event_item_lottery"): return

    logger.info(f"Button `{button_custom_id}` pressed")

def setup(bot):
  bot.add_cog(DTEventItemLottery(bot))
