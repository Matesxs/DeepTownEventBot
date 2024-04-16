import disnake
from disnake.ext import commands
from table2ascii import table2ascii
from table2ascii.alignment import Alignment

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from config import cooldowns
from config.strings import Strings
from utils import message_utils, string_manipulation, dt_autocomplete
from features.views.paginator import EmbedView
from database import dt_items_repo

logger = setup_custom_logger(__name__)

class DTItems(Base_Cog):
  def __init__(self, bot):
    super(DTItems, self).__init__(bot, __file__)

  @commands.slash_command(name="items")
  async def item_commands(self, inter: disnake.CommandInteraction):
    pass

  @item_commands.sub_command(name="list", description=Strings.dt_items_list_description)
  @cooldowns.long_cooldown
  async def list_dt_items(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    items = await dt_items_repo.get_all_dt_items()
    if not items:
      return await message_utils.generate_error_message(inter, Strings.dt_items_list_dt_items_no_items)

    item_data = [(string_manipulation.truncate_string(item.name, 16), item.item_source, f"{string_manipulation.format_number(item.value, 1)}") for item in items]
    item_table_strings = table2ascii(["Name", "Source", "Value"], item_data, alignments=[Alignment.LEFT, Alignment.LEFT, Alignment.RIGHT]).split("\n")

    pages = []
    while item_table_strings:
      data_string, item_table_strings = string_manipulation.add_string_until_length(item_table_strings, 4000, "\n", 42)
      embed = disnake.Embed(title="Deep Town Items", description=f"```\n{data_string}\n```", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(embed, inter.author)
      pages.append(embed)

    embed_view = EmbedView(inter.author, pages)
    await embed_view.run(inter)

  @item_commands.sub_command(name="search", description=Strings.dt_items_search_description)
  @cooldowns.default_cooldown
  async def search_dt_items(self, inter: disnake.CommandInteraction,
                            name: str = commands.Param(description=Strings.dt_item_name_parameter_description, autocomplete=dt_autocomplete.autocomplete_item)):
    await inter.response.defer(with_message=True)

    item = await dt_items_repo.get_dt_item(name)
    if item is None:
      return await message_utils.generate_error_message(inter, Strings.dt_item_not_found)

    component_strings = [f"{int(comp.amount * item.crafting_batch_size)}x {comp.component_item_name}" for comp in item.components_data]
    pages = []
    while component_strings:
      final_description, component_strings = string_manipulation.add_string_until_length(component_strings, 2000, "\n", 10)

      embed = disnake.Embed(title=item.name, description=f"Components:\n{final_description}", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(embed, inter.author)
      embed.add_field(name="Type", value=f"{item.item_type}")
      embed.add_field(name="Source", value=f"{item.item_source}")
      if item.item_type == dt_items_repo.ItemType.CRAFTABLE:
        embed.add_field(name="Crafting time", value=f"{item.crafting_time * item.crafting_batch_size}s")
        embed.add_field(name="Cummulative crafting time per item", value=f"{item.cumulative_crafting_time_per_item}s")
        embed.add_field(name="Batch size", value=f"{item.crafting_batch_size}")
      if item.value > 0:
        embed.add_field(name="Event value", value=f"{item.value}")

      pages.append(embed)

    embed_view = EmbedView(inter.author, pages)
    await embed_view.run(inter)

def setup(bot):
  bot.add_cog(DTItems(bot))
