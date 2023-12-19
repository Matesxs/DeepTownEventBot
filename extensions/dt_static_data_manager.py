import disnake
from disnake.ext import commands
from table2ascii import table2ascii
from table2ascii.alignment import Alignment

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from config import cooldowns, Strings, permissions
from database import dt_items_repo
from utils import message_utils, dt_autocomplete, string_manipulation
from features.views.paginator import EmbedView

logger = setup_custom_logger(__name__)

class DTStaticDataManager(Base_Cog):
  def __init__(self, bot):
    super(DTStaticDataManager, self).__init__(bot, __file__)

  @commands.slash_command()
  @permissions.bot_developer()
  async def static_data(self, inter: disnake.CommandInteraction):
    pass

  @static_data.sub_command_group(name="item")
  async def item_commands(self, inter: disnake.CommandInteraction):
    pass

  @item_commands.sub_command(name="add", description=Strings.static_data_manager_add_dt_item_description)
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def add_dt_item(self, inter: disnake.CommandInteraction,
                        name: str = commands.Param(description=Strings.static_data_manager_add_remove_dt_item_name_param_description),
                        item_type: dt_items_repo.ItemType = commands.Param(description=Strings.static_data_manager_add_dt_item_type_param_description),
                        item_source: dt_items_repo.ItemSource = commands.Param(description=Strings.static_data_manager_add_dt_item_source_param_description),
                        value: float = commands.Param(default=0.0, min_value=0.0, description=Strings.static_data_manager_add_dt_item_value_param_description),
                        crafting_time: float = commands.Param(default=0.0, min_value=0.0, description=Strings.static_data_manager_add_dt_item_crafting_time_param_description),
                        crafting_batch_size: int = commands.Param(default=1, min_value=1, description=Strings.static_data_manager_add_dt_item_crafting_batch_size_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    item_type = dt_items_repo.ItemType(item_type)
    item_source = dt_items_repo.ItemSource(item_source)

    await dt_items_repo.set_dt_item(name, item_type, item_source, value, crafting_time, crafting_batch_size)

    if item_type == dt_items_repo.ItemType.CRAFTABLE:
      await message_utils.generate_success_message(inter, Strings.static_data_manager_add_dt_item_success_craftable(name=name, item_type=item_type, value=value, crafting_time=crafting_time))
    else:
      await message_utils.generate_success_message(inter, Strings.static_data_manager_add_dt_item_success_noncraftable(name=name, item_type=item_type, value=value))

  @item_commands.sub_command(name="remove", description=Strings.static_data_manager_remove_dt_item_description)
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def remove_dt_item(self, inter: disnake.CommandInteraction,
                           name: str = commands.Param(description=Strings.static_data_manager_add_remove_dt_item_name_param_description, autocomplete=dt_autocomplete.autocomplete_item)):
    await inter.response.defer(with_message=True, ephemeral=True)
    if await dt_items_repo.remove_dt_item(name):

      await message_utils.generate_success_message(inter, Strings.static_data_manager_remove_dt_item_success(name=name))
    else:
      await message_utils.generate_error_message(inter, Strings.static_data_manager_remove_dt_item_failed(name=name))

  @item_commands.sub_command(name="list", description=Strings.static_data_manager_list_dt_items_description)
  @cooldowns.default_cooldown
  async def list_dt_items(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    items = await dt_items_repo.get_all_dt_items()
    if not items:
      return await message_utils.generate_error_message(inter, Strings.static_data_manager_list_dt_items_no_items)

    item_data = [(string_manipulation.truncate_string(item.name, 20), item.item_source, f"{string_manipulation.format_number(item.value, 2)}") for item in items]
    item_table_strings = table2ascii(["Name", "Source", "Value"], item_data, alignments=[Alignment.LEFT, Alignment.LEFT, Alignment.RIGHT]).split("\n")

    pages = []
    while item_table_strings:
      data_string, item_table_strings = string_manipulation.add_string_until_length(item_table_strings, 2000, "\n")
      embed = disnake.Embed(title="Deep Town Items", description=f"```\n{data_string}\n```", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(embed, inter.author)
      pages.append(embed)

    embed_view = EmbedView(inter.author, pages)
    await embed_view.run(inter)

  @item_commands.sub_command(name="modify_component", description=Strings.static_data_manager_modify_dt_item_component_description)
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def modify_dt_item_component(self, inter: disnake.CommandInteraction,
                                     target_item: str = commands.Param(description=Strings.static_data_manager_modify_dt_item_component_target_item_param_description, autocomplete=dt_autocomplete.autocomplete_craftable_item),
                                     component_item: str = commands.Param(description=Strings.static_data_manager_modify_dt_item_component_component_item_param_description, autocomplete=dt_autocomplete.autocomplete_item),
                                     amount: float = commands.Param(default=1.0, min_value=0.0, description=Strings.static_data_manager_modify_dt_item_component_amount_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    target_item_ = await dt_items_repo.get_dt_item(target_item)
    if target_item_ is None:
      return await message_utils.generate_error_message(inter, Strings.static_data_manager_target_item_not_found)

    if target_item_.item_type != dt_items_repo.ItemType.CRAFTABLE:
      return await message_utils.generate_error_message(inter, Strings.static_data_manager_modify_dt_item_component_target_not_craftable)

    if (await dt_items_repo.get_dt_item(component_item)) is None:
      return await message_utils.generate_error_message(inter, Strings.static_data_manager_modify_dt_item_component_component_not_found)

    if amount == 0:
      if await dt_items_repo.remove_component_mapping(target_item, component_item):
        await message_utils.generate_success_message(inter, Strings.static_data_manager_modify_dt_item_component_removed(component_item=component_item, target_item=target_item))
      else:
        await message_utils.generate_error_message(inter, Strings.static_data_manager_modify_dt_item_component_remove_failed(component_item=component_item, target_item=target_item))
    else:
      await dt_items_repo.set_component_mapping(target_item, component_item, amount)
      await message_utils.generate_success_message(inter, Strings.static_data_manager_modify_dt_item_component_added(target_item=target_item, component_item=component_item, amount=amount))

  @item_commands.sub_command(name="remove_components", description=Strings.static_data_manager_remove_dt_item_components_description)
  @cooldowns.short_cooldown
  @commands.is_owner()
  async def remove_dt_item_components(self, inter: disnake.CommandInteraction,
                                      target_item: str = commands.Param(description=Strings.static_data_manager_remove_dt_item_components_target_item_param_description, autocomplete=dt_autocomplete.autocomplete_craftable_item)):
    await inter.response.defer(with_message=True, ephemeral=True)

    target_item_ = await dt_items_repo.get_dt_item(target_item)
    if target_item_ is None:
      return await message_utils.generate_error_message(inter, Strings.static_data_manager_target_item_not_found)

    if await dt_items_repo.remove_all_component_mappings(target_item):
      await message_utils.generate_success_message(inter, Strings.static_data_manager_remove_dt_item_components_removed(target_item=target_item))
    else:
      await message_utils.generate_error_message(inter, Strings.static_data_manager_remove_dt_item_components_failed(target_item=target_item))

def setup(bot):
  bot.add_cog(DTStaticDataManager(bot))
