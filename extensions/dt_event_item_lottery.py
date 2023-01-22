import disnake
import datetime
from typing import Optional
from disnake.ext import commands
from table2ascii import table2ascii, Alignment

from config import cooldowns, permissions
from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from utils import dt_helpers, message_utils, dt_autocomplete, string_manipulation
from database import dt_items_repo, dt_event_item_lottery_repo

logger = setup_custom_logger(__name__)

class DTEventItemLottery(Base_Cog):
  def __init__(self, bot):
    super(DTEventItemLottery, self).__init__(bot, __file__)

  @commands.slash_command(name="lottery")
  @commands.guild_only()
  async def lottery_command(self, inter: disnake.CommandInteraction):
    pass

  @lottery_command.sub_command(name="create", description="Create event items lotery for next event")
  @cooldowns.long_cooldown
  async def create_lottery(self, inter: disnake.CommandInteraction,
                           guessed_4_reward_item: Optional[str]=commands.Param(default=None, description="Reward item for guessing 4 event items right", autocomplete=dt_autocomplete.autocomplete_item),
                           guessed_4_reward_item_amount: int=commands.Param(default=0, min_value=0, description="Number of reward items for guessing 4 event items right"),
                           guessed_3_reward_item: Optional[str] = commands.Param(default=None, description="Reward item for guessing 3 event items right", autocomplete=dt_autocomplete.autocomplete_item),
                           guessed_3_reward_item_amount: int = commands.Param(default=0, min_value=0, description="Number of reward items for guessing 3 event items right"),
                           guessed_2_reward_item: Optional[str] = commands.Param(default=None, description="Reward item for guessing 2 event items right", autocomplete=dt_autocomplete.autocomplete_item),
                           guessed_2_reward_item_amount: int = commands.Param(default=0, min_value=0, description="Number of reward items for guessing 2 event items right"),
                           guessed_1_reward_item: Optional[str] = commands.Param(default=None, description="Reward item for guessing 1 event item right", autocomplete=dt_autocomplete.autocomplete_item),
                           guessed_1_reward_item_amount: int = commands.Param(default=0, min_value=0, description="Number of reward items for guessing 1 event item right"),
                           can_show_guesses: bool=commands.Param(default=False, description="Can users request current guesses")):
    await inter.response.defer(with_message=True)

    if guessed_4_reward_item is not None:
      guessed_4_reward_item_ = await dt_items_repo.get_dt_item(guessed_4_reward_item)
      if guessed_4_reward_item_ is None:
        return await message_utils.generate_error_message(inter, f"`{guessed_4_reward_item}` is not valid item")
      guessed_4_reward_item = guessed_4_reward_item_
    if guessed_3_reward_item is not None:
      guessed_3_reward_item_ = await dt_items_repo.get_dt_item(guessed_3_reward_item)
      if guessed_3_reward_item_ is None:
        return await message_utils.generate_error_message(inter, f"`{guessed_3_reward_item}` is not valid item")
      guessed_3_reward_item = guessed_3_reward_item_
    if guessed_2_reward_item is not None:
      guessed_2_reward_item_ = await dt_items_repo.get_dt_item(guessed_2_reward_item)
      if guessed_2_reward_item_ is None:
        return await message_utils.generate_error_message(inter, f"`{guessed_2_reward_item}` is not valid item")
      guessed_2_reward_item = guessed_2_reward_item_
    if guessed_1_reward_item is not None:
      guessed_1_reward_item_ = await dt_items_repo.get_dt_item(guessed_1_reward_item)
      if guessed_1_reward_item_ is None:
        return await message_utils.generate_error_message(inter, f"`{guessed_1_reward_item}` is not valid item")
      guessed_1_reward_item = guessed_1_reward_item_

    table_data = [(4, string_manipulation.format_number(guessed_4_reward_item_amount) if guessed_4_reward_item is not None and guessed_4_reward_item_amount > 0 else " ", string_manipulation.truncate_string(guessed_4_reward_item.name, 20) if guessed_4_reward_item is not None and guessed_4_reward_item_amount > 0 else "*No Reward*"),
                  (3, string_manipulation.format_number(guessed_3_reward_item_amount) if guessed_3_reward_item is not None and guessed_3_reward_item_amount > 0 else " ", string_manipulation.truncate_string(guessed_3_reward_item.name, 20) if guessed_3_reward_item is not None and guessed_3_reward_item_amount > 0 else "*No Reward*"),
                  (2, string_manipulation.format_number(guessed_2_reward_item_amount) if guessed_2_reward_item is not None and guessed_2_reward_item_amount > 0 else " ", string_manipulation.truncate_string(guessed_2_reward_item.name, 20) if guessed_2_reward_item is not None and guessed_2_reward_item_amount > 0 else "*No Reward*"),
                  (1, string_manipulation.format_number(guessed_1_reward_item_amount) if guessed_1_reward_item is not None and guessed_1_reward_item_amount > 0 else " ", string_manipulation.truncate_string(guessed_1_reward_item.name, 20) if guessed_1_reward_item is not None and guessed_1_reward_item_amount > 0 else "*No Reward*")]
    lottery_table = table2ascii(["Guessed", "Amount", "Reward"], table_data, alignments=[Alignment.RIGHT, Alignment.RIGHT, Alignment.LEFT], first_col_heading=True)

    next_year, next_week = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))
    lottery_embed = disnake.Embed(title=f"Event items lottery for `{next_year} {next_week}`", description=f"```\n{lottery_table}\n```", color=disnake.Color.blurple())
    message_utils.add_author_footer(lottery_embed, inter.author)

    await inter.send(embed=lottery_embed)
    message = await inter.original_message()
    if message is None:
      return await message_utils.generate_error_message(inter, "INTERNAL ERROR: Failed to get lottery message")

    lottery = await dt_event_item_lottery_repo.create_event_item_lottery(inter.guild, inter.author, message,
                                                                         guessed_4_reward_item, guessed_4_reward_item_amount,
                                                                         guessed_3_reward_item, guessed_3_reward_item_amount,
                                                                         guessed_2_reward_item, guessed_2_reward_item_amount,
                                                                         guessed_1_reward_item, guessed_1_reward_item_amount)
    if lottery is None:
      return await message_utils.generate_error_message(inter, "You already have lottery created for next event")

    buttons = [disnake.ui.Button(emoji="🗑️", custom_id=f"event_item_lottery:remove:{lottery.id}", style=disnake.ButtonStyle.red)]
    if can_show_guesses:
      buttons.append(disnake.ui.Button(emoji="🧾", custom_id=f"event_item_lottery:show:{lottery.id}", style=disnake.ButtonStyle.blurple))
    await message.edit(components=buttons)

  @lottery_command.sub_command(name="guess", description="Make a guess for next event items")
  @cooldowns.long_cooldown
  async def lottery_make_guess(self, inter: disnake.CommandInteraction,
                               guess_item_1: Optional[str] = commands.Param(default=None, description="Item guess 1", autocomplete=dt_autocomplete.autocomplete_item),
                               guess_item_2: Optional[str] = commands.Param(default=None, description="Item guess 2", autocomplete=dt_autocomplete.autocomplete_item),
                               guess_item_3: Optional[str] = commands.Param(default=None, description="Item guess 3", autocomplete=dt_autocomplete.autocomplete_item),
                               guess_item_4: Optional[str] = commands.Param(default=None, description="Item guess 4", autocomplete=dt_autocomplete.autocomplete_item)):
    await inter.response.defer(with_message=True, ephemeral=True)

    if not (await dt_event_item_lottery_repo.any_lotteries_active_next_event(inter.guild_id)):
      return await message_utils.generate_error_message(inter, "No active lotteries for next event, try it later")

    items = []
    if guess_item_1 is not None:
      guess_item_1_ = await dt_items_repo.get_dt_item(guess_item_1)
      if guess_item_1_ is None:
        return await message_utils.generate_error_message(inter, f"`{guess_item_1}` is not valid item")
      items.append(guess_item_1_)
    if guess_item_2 is not None:
      guess_item_2_ = await dt_items_repo.get_dt_item(guess_item_2)
      if guess_item_2_ is None:
        return await message_utils.generate_error_message(inter, f"`{guess_item_2}` is not valid item")
      items.append(guess_item_2_)
    if guess_item_3 is not None:
      guess_item_3_ = await dt_items_repo.get_dt_item(guess_item_3)
      if guess_item_3_ is None:
        return await message_utils.generate_error_message(inter, f"`{guess_item_3}` is not valid item")
      items.append(guess_item_3_)
    if guess_item_4 is not None:
      guess_item_4_ = await dt_items_repo.get_dt_item(guess_item_4)
      if guess_item_4_ is None:
        return await message_utils.generate_error_message(inter, f"`{guess_item_4}` is not valid item")
      items.append(guess_item_4_)

    guess = await dt_event_item_lottery_repo.make_next_event_guess(inter.guild, inter.author, items)
    if guess is None:
      return await message_utils.generate_error_message(inter, "Guess failed, invalid items - duplicates")

    guessed_item_names_string = ", ".join([i.name for i in items])
    await message_utils.generate_success_message(inter, f"Guess registered for event `{guess.event_specification.event_year} {guess.event_specification.event_week}`\n`{guessed_item_names_string}`")

  @commands.Cog.listener()
  async def on_button_click(self, inter: disnake.MessageInteraction):
    if not isinstance(inter.component, disnake.Button): return

    button_custom_id = inter.component.custom_id
    if button_custom_id is None or not button_custom_id.startswith("event_item_lottery"): return
    await inter.response.defer()

    data = button_custom_id.split(":")
    command = data[1]
    lottery_id = int(data[2])

    lottery = await dt_event_item_lottery_repo.get_event_item_lottery(lottery_id)
    if lottery is None:
      await message_utils.delete_message(self.bot, inter.message)
      return await message_utils.generate_error_message(inter, "Lotery doesn't exist, removing invalid message")

    if command == "remove":
      if inter.author.id == int(lottery.author_id) or (await permissions.predicate_is_guild_administrator(inter)):
        await message_utils.delete_message(self.bot, inter.message)
        await dt_event_item_lottery_repo.remove_lottery(lottery.id)
        await message_utils.generate_success_message(inter, "Lotery removed")
      else:
        await message_utils.generate_error_message(inter, "You can't remove this lotery because you are not author")
    elif command == "show":
      pass

def setup(bot):
  bot.add_cog(DTEventItemLottery(bot))
