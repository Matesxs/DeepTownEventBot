import disnake
from disnake.ext import commands
from table2ascii import table2ascii
from table2ascii.alignment import Alignment

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from config import cooldowns
from config.strings import Strings
from utils import message_utils, string_manipulation
from features.views.paginator import EmbedView
from database import dt_items_repo

logger = setup_custom_logger(__name__)

class DTItems(Base_Cog):
  def __init__(self, bot):
    super(DTItems, self).__init__(bot, __file__)

  @commands.slash_command(name="items")
  async def item_commands(self, inter: disnake.CommandInteraction):
    pass

  @item_commands.sub_command(name="list", description=Strings.dt_items_list_dt_items_description)
  @cooldowns.long_cooldown
  async def list_dt_items(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    items = await dt_items_repo.get_all_dt_items()
    if not items:
      return await message_utils.generate_error_message(inter, Strings.dt_items_list_dt_items_no_items)

    item_data = [(string_manipulation.truncate_string(item.name, 20), item.item_source, f"{string_manipulation.format_number(item.value, 2)}") for item in items]
    item_table_strings = table2ascii(["Name", "Source", "Value"], item_data, alignments=[Alignment.LEFT, Alignment.LEFT, Alignment.RIGHT]).split("\n")

    pages = []
    while item_table_strings:
      data_string, item_table_strings = string_manipulation.add_string_until_length(item_table_strings, 4000, "\n", 42)
      embed = disnake.Embed(title="Deep Town Items", description=f"```\n{data_string}\n```", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(embed, inter.author)
      pages.append(embed)

    embed_view = EmbedView(inter.author, pages)
    await embed_view.run(inter)

def setup(bot):
  bot.add_cog(DTItems(bot))
