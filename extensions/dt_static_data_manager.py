import disnake
from disnake.ext import commands

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from config import cooldowns, Strings
from database import dt_items_repo, session_maker
from utils import message_utils, dt_autocomplete, command_utils

logger = setup_custom_logger(__name__)

class DTStaticDataManager(Base_Cog):
  def __init__(self, bot):
    super(DTStaticDataManager, self).__init__(bot, __file__)

  @command_utils.master_only_slash_command()
  @commands.is_owner()
  async def static_data(self, inter: disnake.CommandInteraction):
    pass

  @static_data.sub_command_group(name="configure_item")
  async def item_configuration_commands(self, inter: disnake.CommandInteraction):
    pass

  @item_configuration_commands.sub_command(name="add", description=Strings.static_data_manager_add_dt_item_description)
  @cooldowns.short_cooldown
  async def add_dt_item(self, inter: disnake.CommandInteraction,
                        name: str = commands.Param(description=Strings.dt_item_name_parameter_description, max_length=25),
                        item_type: dt_items_repo.ItemType = commands.Param(description=Strings.static_data_manager_add_dt_item_type_param_description),
                        item_source: dt_items_repo.ItemSource = commands.Param(description=Strings.static_data_manager_add_dt_item_source_param_description),
                        value: float = commands.Param(default=0.0, min_value=0.0, description=Strings.static_data_manager_add_dt_item_value_param_description),
                        crafting_time: float = commands.Param(default=0.0, min_value=0.0, description=Strings.static_data_manager_add_dt_item_crafting_time_param_description),
                        crafting_batch_size: int = commands.Param(default=1, min_value=1, description=Strings.static_data_manager_add_dt_item_crafting_batch_size_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    item_type = dt_items_repo.ItemType(item_type)
    item_source = dt_items_repo.ItemSource(item_source)

    with session_maker() as session:
      await dt_items_repo.set_dt_item(session, name, item_type, item_source, value, crafting_time, crafting_batch_size)

    if item_type == dt_items_repo.ItemType.CRAFTABLE:
      await message_utils.generate_success_message(inter, Strings.static_data_manager_add_dt_item_success_craftable(name=name, item_type=item_type, value=value, crafting_time=crafting_time))
    else:
      await message_utils.generate_success_message(inter, Strings.static_data_manager_add_dt_item_success_noncraftable(name=name, item_type=item_type, value=value))

  @item_configuration_commands.sub_command(name="remove", description=Strings.static_data_manager_remove_dt_item_description)
  @cooldowns.short_cooldown
  async def remove_dt_item(self, inter: disnake.CommandInteraction,
                           name: str = commands.Param(description=Strings.dt_item_name_parameter_description, autocomplete=dt_autocomplete.autocomplete_item)):
    await inter.response.defer(with_message=True, ephemeral=True)

    with session_maker() as session:
      if await dt_items_repo.remove_dt_item(session, name):
        await message_utils.generate_success_message(inter, Strings.static_data_manager_remove_dt_item_success(name=name))
      else:
        await message_utils.generate_error_message(inter, Strings.static_data_manager_remove_dt_item_failed(name=name))

  @item_configuration_commands.sub_command(name="modify_component", description=Strings.static_data_manager_modify_dt_item_component_description)
  @cooldowns.short_cooldown
  async def modify_dt_item_component(self, inter: disnake.CommandInteraction,
                                     target_item: str = commands.Param(description=Strings.static_data_manager_modify_dt_item_component_target_item_param_description, autocomplete=dt_autocomplete.autocomplete_craftable_item),
                                     component_item: str = commands.Param(description=Strings.static_data_manager_modify_dt_item_component_component_item_param_description, autocomplete=dt_autocomplete.autocomplete_item),
                                     amount: float = commands.Param(default=1.0, min_value=0.0, description=Strings.static_data_manager_modify_dt_item_component_amount_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    with session_maker() as session:
      target_item_ = await dt_items_repo.get_dt_item(session, target_item)
      if target_item_ is None:
        return await message_utils.generate_error_message(inter, Strings.dt_item_not_found)

      if target_item_.item_type != dt_items_repo.ItemType.CRAFTABLE:
        return await message_utils.generate_error_message(inter, Strings.static_data_manager_modify_dt_item_component_target_not_craftable)

      if (await dt_items_repo.get_dt_item(session, component_item)) is None:
        return await message_utils.generate_error_message(inter, Strings.static_data_manager_modify_dt_item_component_component_not_found)

      if amount == 0:
        if await dt_items_repo.remove_component_mapping(session, target_item, component_item):
          await message_utils.generate_success_message(inter, Strings.static_data_manager_modify_dt_item_component_removed(component_item=component_item, target_item=target_item))
        else:
          await message_utils.generate_error_message(inter, Strings.static_data_manager_modify_dt_item_component_remove_failed(component_item=component_item, target_item=target_item))
      else:
        await dt_items_repo.set_component_mapping(session, target_item, component_item, amount)
        await message_utils.generate_success_message(inter, Strings.static_data_manager_modify_dt_item_component_added(target_item=target_item, component_item=component_item, amount=amount))

  @item_configuration_commands.sub_command(name="remove_components", description=Strings.static_data_manager_remove_dt_item_components_description)
  @cooldowns.short_cooldown
  async def remove_dt_item_components(self, inter: disnake.CommandInteraction,
                                      target_item: str = commands.Param(description=Strings.static_data_manager_remove_dt_item_components_target_item_param_description, autocomplete=dt_autocomplete.autocomplete_craftable_item)):
    await inter.response.defer(with_message=True, ephemeral=True)

    with session_maker() as session:
      target_item_ = await dt_items_repo.get_dt_item(session, target_item)
      if target_item_ is None:
        return await message_utils.generate_error_message(inter, Strings.dt_item_not_found)

      if await dt_items_repo.remove_all_component_mappings(session, target_item):
        await message_utils.generate_success_message(inter, Strings.static_data_manager_remove_dt_item_components_removed(target_item=target_item))
      else:
        await message_utils.generate_error_message(inter, Strings.static_data_manager_remove_dt_item_components_failed(target_item=target_item))

def setup(bot):
  bot.add_cog(DTStaticDataManager(bot))
