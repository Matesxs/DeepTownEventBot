import asyncio
import datetime
import disnake
from typing import Optional
from disnake.ext import commands, tasks
from Levenshtein import ratio
import math
from table2ascii import table2ascii, Alignment

from config import cooldowns, permissions
from config.strings import Strings
from config import config
from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from utils import message_utils, dt_autocomplete, items_lottery, dt_helpers, string_manipulation
import database
from database import dt_items_repo, dt_event_item_lottery_repo, run_commit, event_participation_repo, automatic_lottery_guesses_whitelist_repo
from features.views import confirm_view
from features.views.paginator import EmbedView

logger = setup_custom_logger(__name__)

async def make_guess(inter: disnake.CommandInteraction | commands.Context | disnake.Message,
                     author: disnake.Member,
                     guess_item_1: Optional[str],
                     guess_item_2: Optional[str],
                     guess_item_3: Optional[str],
                     guess_item_4: Optional[str]):
  items = []
  if guess_item_1 is not None:
    guess_item_1_ = await dt_items_repo.get_dt_item(guess_item_1)
    if guess_item_1_ is None:
      return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guess_item_1))
    items.append(guess_item_1_)
  if guess_item_2 is not None:
    guess_item_2_ = await dt_items_repo.get_dt_item(guess_item_2)
    if guess_item_2_ is None:
      return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guess_item_2))
    items.append(guess_item_2_)
  if guess_item_3 is not None:
    guess_item_3_ = await dt_items_repo.get_dt_item(guess_item_3)
    if guess_item_3_ is None:
      return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guess_item_3))
    items.append(guess_item_3_)
  if guess_item_4 is not None:
    guess_item_4_ = await dt_items_repo.get_dt_item(guess_item_4)
    if guess_item_4_ is None:
      return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guess_item_4))
    items.append(guess_item_4_)

  if not items:
    return await message_utils.generate_error_message(inter, Strings.lottery_guess_no_items)

  guess = await dt_event_item_lottery_repo.make_next_event_guess(author, items)
  if guess is None:
    return await message_utils.generate_error_message(inter, Strings.lottery_guess_item_duplicates)

  guessed_item_names_string = ", ".join([i.name for i in items])
  await message_utils.generate_success_message(inter, Strings.lottery_guess_registered(event_year=guess.event_specification.event_year, event_week=guess.event_specification.event_week, items=guessed_item_names_string))


async def handle_guess_message(message: disnake.Message):
  async def already_guessed():
    already_existing_guess = await dt_event_item_lottery_repo.get_guess(message.guild.id, message.author.id, event_spec.event_id)

    if already_existing_guess is not None:
      already_existing_guessed_names = [guessed_item.item_name for guessed_item in already_existing_guess.guessed_lotery_items]
      if all([now_guessed_item_name in already_existing_guessed_names for now_guessed_item_name in item_names]) and len(already_existing_guessed_names) == len(item_names):
        return True

    return False

  if message.guild is None: return
  if message.author.bot or message.author.system: return
  if message.content == "" or message.content.startswith(config.base.command_prefix): return
  if not message.channel.permissions_for(message.guild.me).send_messages: return

  message_lines = message.content.split("\n")
  if len(message_lines) > 4: return

  if not await automatic_lottery_guesses_whitelist_repo.is_on_whitelist(message.guild.id, message.channel.id):
    return

  all_item_names = await dt_items_repo.get_all_item_names()
  all_item_names = [(name, name.lower()) for name in all_item_names]

  guessed_items_data = []
  for message_line in message_lines:
    message_line = message_line.lower()

    max_score = 0
    guessed_item_name = None
    for item_name, item_name_lower in all_item_names:
      score = ratio(message_line, item_name_lower)
      if score <= 0.1: continue

      if score > max_score:
        max_score = score
        guessed_item_name = item_name

      if max_score > 0.9:
        break

    if max_score > 0.7:
      guessed_items_data.append((guessed_item_name, max_score * 100))

  if guessed_items_data:
    guessed_items_data.sort(key=lambda x: x[1], reverse=True)

    all_sure = True
    item_names = []
    deduplicated_data = []
    for data in guessed_items_data:
      if data[0] not in item_names:
        if data[1] < 90:
          all_sure = False

        item_names.append(data[0])
        deduplicated_data.append(data)

    year, week = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))
    event_spec = await event_participation_repo.get_or_create_event_specification(year, week)

    if await already_guessed():
      return

    if len(item_names) and all_sure:
      await make_guess(message, message.author, *item_names)
    else:
      items_list_string = "\n".join([f"`{item_name}` - {confidence:.1f}% confidence" for item_name, confidence in deduplicated_data])
      prompt_string = f"Detected lottery guess\nAre these items correct and do you want to add them as a guess to lottery?\n\n**Guessed items:**\n{items_list_string}"

      confirmation_view = confirm_view.ConfirmView(message, prompt_string)
      if await confirmation_view.run():
        await confirmation_view.wait()

        if confirmation_view.get_result():
          if await already_guessed():
            return

          await make_guess(message, message.author, *item_names)

class DTEventItemLottery(Base_Cog):
  def __init__(self, bot):
    super(DTEventItemLottery, self).__init__(bot, __file__)

  @commands.Cog.listener()
  async def on_ready(self):
    if not self.delete_long_closed_lotteries_task.is_running():
      self.delete_long_closed_lotteries_task.start()

    if not self.notify_lottery_closed_task.is_running():
      self.notify_lottery_closed_task.start()

  def cog_load(self) -> None:
    if self.bot.is_ready():
      if not self.delete_long_closed_lotteries_task.is_running():
        self.delete_long_closed_lotteries_task.start()

      if not self.notify_lottery_closed_task.is_running():
        self.notify_lottery_closed_task.start()

  def cog_unload(self) -> None:
    if self.delete_long_closed_lotteries_task.is_running():
      self.delete_long_closed_lotteries_task.cancel()

    if self.notify_lottery_closed_task.is_running():
      self.notify_lottery_closed_task.cancel()

  @commands.slash_command(name="lottery")
  async def lottery_command(self, inter: disnake.CommandInteraction):
    pass

  @lottery_command.sub_command(name="create", description=Strings.lottery_create_description)
  @commands.guild_only()
  @cooldowns.long_cooldown
  async def create_lottery(self, inter: disnake.CommandInteraction,
                           guessed_4_reward_item: Optional[str] = commands.Param(default=None, description=Strings.lottery_create_reward_item_param_description(item_number=4), autocomplete=dt_autocomplete.autocomplete_item),
                           guessed_4_reward_item_amount: int=commands.Param(default=0, min_value=0, description=Strings.lottery_create_reward_item_amount_param_description(item_number=4)),
                           guessed_3_reward_item: Optional[str] = commands.Param(default=None, description=Strings.lottery_create_reward_item_param_description(item_number=3), autocomplete=dt_autocomplete.autocomplete_item),
                           guessed_3_reward_item_amount: int = commands.Param(default=0, min_value=0, description=Strings.lottery_create_reward_item_amount_param_description(item_number=3)),
                           guessed_2_reward_item: Optional[str] = commands.Param(default=None, description=Strings.lottery_create_reward_item_param_description(item_number=2), autocomplete=dt_autocomplete.autocomplete_item),
                           guessed_2_reward_item_amount: int = commands.Param(default=0, min_value=0, description=Strings.lottery_create_reward_item_amount_param_description(item_number=2)),
                           guessed_1_reward_item: Optional[str] = commands.Param(default=None, description=Strings.lottery_create_reward_item_param_description(item_number=1), autocomplete=dt_autocomplete.autocomplete_item),
                           guessed_1_reward_item_amount: int = commands.Param(default=0, min_value=0, description=Strings.lottery_create_reward_item_amount_param_description(item_number=1))):
    await inter.response.defer(with_message=True)

    if (guessed_4_reward_item is None or guessed_4_reward_item_amount == 0) and \
        (guessed_3_reward_item is None or guessed_3_reward_item_amount == 0) and \
        (guessed_2_reward_item is None or guessed_2_reward_item_amount == 0) and \
        (guessed_1_reward_item is None or guessed_1_reward_item_amount == 0):
      return await message_utils.generate_error_message(inter, Strings.lottery_create_no_reward_set)

    if guessed_4_reward_item is not None:
      guessed_4_reward_item_ = await dt_items_repo.get_dt_item(guessed_4_reward_item)
      if guessed_4_reward_item_ is None:
        return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guessed_4_reward_item))
      guessed_4_reward_item = guessed_4_reward_item_
    if guessed_3_reward_item is not None:
      guessed_3_reward_item_ = await dt_items_repo.get_dt_item(guessed_3_reward_item)
      if guessed_3_reward_item_ is None:
        return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guessed_3_reward_item))
      guessed_3_reward_item = guessed_3_reward_item_
    if guessed_2_reward_item is not None:
      guessed_2_reward_item_ = await dt_items_repo.get_dt_item(guessed_2_reward_item)
      if guessed_2_reward_item_ is None:
        return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guessed_2_reward_item))
      guessed_2_reward_item = guessed_2_reward_item_
    if guessed_1_reward_item is not None:
      guessed_1_reward_item_ = await dt_items_repo.get_dt_item(guessed_1_reward_item)
      if guessed_1_reward_item_ is None:
        return await message_utils.generate_error_message(inter, Strings.lottery_invalid_item(item_name=guessed_1_reward_item))
      guessed_1_reward_item = guessed_1_reward_item_

    orig_message = await inter.original_message()
    lottery = await dt_event_item_lottery_repo.create_event_item_lottery(inter.author, orig_message.channel,
                                                                         guessed_4_reward_item, guessed_4_reward_item_amount,
                                                                         guessed_3_reward_item, guessed_3_reward_item_amount,
                                                                         guessed_2_reward_item, guessed_2_reward_item_amount,
                                                                         guessed_1_reward_item, guessed_1_reward_item_amount)
    if lottery is None:
      return await message_utils.generate_error_message(inter, Strings.lottery_already_created)

    await items_lottery.create_lottery(inter.author, orig_message, lottery, True)

  @lottery_command.sub_command(name="list", description=Strings.lottery_list_description)
  @commands.guild_only()
  @cooldowns.long_cooldown
  async def lottery_list(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    lotteries = await dt_event_item_lottery_repo.get_lotteries_in_guild(inter.guild_id)
    if not lotteries:
      return await message_utils.generate_error_message(inter, Strings.lottery_list_no_lotteries)

    lottery_pages = []
    for lottery in lotteries:
      table_data = [(4, f"{string_manipulation.format_number(lottery.guessed_4_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_4_reward_item_name, 20)}" if lottery.guessed_4_reward_item_name is not None and lottery.guessed_4_item_reward_amount > 0 else "*No Reward*"),
                    (3, f"{string_manipulation.format_number(lottery.guessed_3_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_3_reward_item_name, 20)}" if lottery.guessed_3_reward_item_name is not None and lottery.guessed_3_item_reward_amount > 0 else "*No Reward*"),
                    (2, f"{string_manipulation.format_number(lottery.guessed_2_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_2_reward_item_name, 20)}" if lottery.guessed_2_reward_item_name is not None and lottery.guessed_2_item_reward_amount > 0 else "*No Reward*"),
                    (1, f"{string_manipulation.format_number(lottery.guessed_1_item_reward_amount)} {string_manipulation.truncate_string(lottery.guessed_1_reward_item_name, 20)}" if lottery.guessed_1_reward_item_name is not None and lottery.guessed_1_item_reward_amount > 0 else "*No Reward*")]
      lottery_table = table2ascii(["Guessed", "Reward"], table_data, alignments=[Alignment.RIGHT, Alignment.LEFT], first_col_heading=True)

      embed = disnake.Embed(title=f"Lottery by {string_manipulation.truncate_string(lottery.member.name, 200)}", description=f"```\n{lottery_table}\n```", color=disnake.Color.dark_blue())
      message_utils.add_author_footer(embed, inter.author)

      lottery_message = await lottery.get_lotery_message(self.bot)
      if lottery_message is not None:
        embed.url = lottery_message.jump_url
      else:
        embed.url = lottery.get_lottery_message_url()

      start_date, end_date = dt_helpers.event_index_to_date_range(lottery.event_specification.event_year, lottery.event_specification.event_week)

      embed.add_field(name="Created", value=f"{lottery.created_at.day}.{lottery.created_at.month}.{lottery.created_at.year}")
      embed.add_field(name="Resolved", value=f"{lottery.closed_at.day}.{lottery.closed_at.month}.{lottery.closed_at.year}" if lottery.closed_at is not None else "Never")
      embed.add_field(name="Closed", value="Yes" if start_date < datetime.datetime.utcnow() else "No")

      embed.add_field(name="For Event", value=f"{lottery.event_specification.event_year} {lottery.event_specification.event_week}")
      embed.add_field(name="\u200b", value="\u200b")
      embed.add_field(name="Event span", value=f"{start_date.day}.{start_date.month}.{start_date.year} - {end_date.day}.{end_date.month}.{end_date.year}")

      lottery_pages.append(embed)
      await asyncio.sleep(0.05)

    embed_view = EmbedView(inter.author, lottery_pages, invisible=True)
    await embed_view.run(inter)

  @lottery_command.sub_command(name="update", description=Strings.lottery_update_description)
  @permissions.bot_developer()
  @cooldowns.long_cooldown
  async def lottery_update(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    result = await items_lottery.process_loterries(self.bot)
    if result is None:
      return await message_utils.generate_success_message(inter, Strings.lottery_update_no_active_lotteries)

    results, guesses_cleared = result
    await message_utils.generate_success_message(inter, Strings.lottery_update_success(results=results, guesses_cleared=guesses_cleared))

  @lottery_command.sub_command_group(name="guess")
  @commands.guild_only()
  @cooldowns.long_cooldown
  async def guess_commands(self, inter: disnake.CommandInteraction):
    pass

  @guess_commands.sub_command(name="create", description=Strings.lottery_guess_create_description)
  async def lottery_make_guess(self, inter: disnake.CommandInteraction,
                               guess_item_1: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=1), autocomplete=dt_autocomplete.autocomplete_item),
                               guess_item_2: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=2), autocomplete=dt_autocomplete.autocomplete_item),
                               guess_item_3: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=3), autocomplete=dt_autocomplete.autocomplete_item),
                               guess_item_4: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=4), autocomplete=dt_autocomplete.autocomplete_item)):
    await inter.response.defer(with_message=True, ephemeral=True)

    await make_guess(inter, inter.author, guess_item_1, guess_item_2, guess_item_3, guess_item_4)

  @guess_commands.sub_command(name="remove", description=Strings.lottery_guess_remove_description)
  async def lottery_remove_guess(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

    year, week = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))
    event_specification = await event_participation_repo.get_or_create_event_specification(year, week)

    if await dt_event_item_lottery_repo.remove_guess(inter.guild_id, inter.author.id, event_specification.event_id):
      await message_utils.generate_success_message(inter, Strings.lottery_guess_removed_sucessfully)
    else:
      await message_utils.generate_error_message(inter, Strings.lottery_guess_no_guess_to_remove)

  @lottery_command.sub_command_group(name="guess_for")
  @commands.guild_only()
  @permissions.guild_administrator_role()
  @cooldowns.long_cooldown
  async def guess_for_commands(self, inter: disnake.CommandInteraction):
    pass

  @guess_for_commands.sub_command(name="create", description=Strings.lottery_guess_for_create_description)
  async def lottery_make_guess_for(self, inter: disnake.CommandInteraction,
                                   author: disnake.Member = commands.Param(description=Strings.lottery_guess_for_author_param_description),
                                   guess_item_1: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=1), autocomplete=dt_autocomplete.autocomplete_item),
                                   guess_item_2: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=2), autocomplete=dt_autocomplete.autocomplete_item),
                                   guess_item_3: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=3), autocomplete=dt_autocomplete.autocomplete_item),
                                   guess_item_4: Optional[str] = commands.Param(default=None, description=Strings.lottery_guess_item_param_description(item_number=4), autocomplete=dt_autocomplete.autocomplete_item)):
    await inter.response.defer(with_message=True, ephemeral=True)

    await make_guess(inter, author, guess_item_1, guess_item_2, guess_item_3, guess_item_4)

  @guess_for_commands.sub_command(name="remove", description=Strings.lottery_guess_for_remove_description)
  async def lottery_remove_guess_for(self, inter: disnake.CommandInteraction,
                                     author: disnake.Member = commands.Param(description=Strings.lottery_guess_for_author_param_description)):
    await inter.response.defer(with_message=True, ephemeral=True)

    year, week = dt_helpers.get_event_index(datetime.datetime.utcnow() + datetime.timedelta(days=7))
    event_specification = await event_participation_repo.get_or_create_event_specification(year, week)

    if await dt_event_item_lottery_repo.remove_guess(inter.guild_id, author.id, event_specification.event_id):
      await message_utils.generate_success_message(inter, Strings.lottery_guess_removed_sucessfully)
    else:
      await message_utils.generate_error_message(inter, Strings.lottery_guess_no_guess_to_remove)

  @lottery_command.sub_command_group(name="auto_guess_whitelist")
  @commands.guild_only()
  @permissions.guild_administrator_role()
  @cooldowns.default_cooldown
  async def auto_lottery_guess_whitelist_commands(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True, ephemeral=True)

  @auto_lottery_guess_whitelist_commands.sub_command(name="add", description=Strings.lottery_auto_guess_whitelist_add_description)
  async def auto_lottery_guess_whitelist_add(self, inter: disnake.CommandInteraction,
                                             channel: disnake.TextChannel=commands.Param(description=Strings.discord_text_channel_param_description)):
    if await automatic_lottery_guesses_whitelist_repo.add_to_whitelist(channel.guild, channel.id):
      return await message_utils.generate_success_message(inter, Strings.lottery_auto_guess_whitelist_add_success(channel=channel.name))
    await message_utils.generate_error_message(inter, Strings.lottery_auto_guess_whitelist_add_failed(channel=channel.name))

  @auto_lottery_guess_whitelist_commands.sub_command(name="list", description=Strings.lottery_auto_guess_whitelist_list_description)
  async def auto_lottery_guess_whitelist_list(self, inter: disnake.CommandInteraction):
    whitelisted_channel_objects = await automatic_lottery_guesses_whitelist_repo.get_whitelist_channels(inter.guild.id)
    whitelisted_channels = []
    for wcho in whitelisted_channel_objects:
      channel = await wcho.get_channel(self.bot)
      if channel is not None:
        whitelisted_channels.append(channel)
      else:
        await database.remove_item(wcho)

    if not whitelisted_channels:
      return await message_utils.generate_error_message(inter, Strings.lottery_auto_guess_whitelist_list_no_channels)

    num_of_batches = math.ceil(len(whitelisted_channels) / 12)
    batches = [whitelisted_channels[i * 12:i * 12 + 12] for i in range(num_of_batches)]

    pages = []
    for batch in batches:
      whitelisted_channels_string = "\n".join([f"[#{channel.name}]({channel.jump_url})" for channel in batch])
      page = disnake.Embed(title="Automatic lottery guesses whitelisted channels", color=disnake.Color.dark_blue(), description=whitelisted_channels_string)
      message_utils.add_author_footer(page, inter.author)
      pages.append(page)

    embed_view = EmbedView(inter.author, pages, invisible=True)
    await embed_view.run(inter)

  @auto_lottery_guess_whitelist_commands.sub_command(name="remove", description=Strings.lottery_auto_guess_whitelist_remove_description)
  async def auto_lottery_guess_whitelist_remove(self, inter: disnake.CommandInteraction,
                                                channel: disnake.TextChannel=commands.Param(description=Strings.discord_text_channel_param_description)):
    if await automatic_lottery_guesses_whitelist_repo.remove_from_whitelist(channel.guild.id, channel.id):
      return await message_utils.generate_success_message(inter, Strings.lottery_auto_guess_whitelist_remove_success(channel=channel.name))
    await message_utils.generate_error_message(inter, Strings.lottery_auto_guess_whitelist_remove_failed(channel=channel.name))

  async def handle_message_edited(self, _, message: disnake.Message):
    await handle_guess_message(message)

  @commands.Cog.listener()
  async def on_message(self, message: disnake.Message):
    await handle_guess_message(message)

  @commands.Cog.listener()
  async def on_button_click(self, inter: disnake.MessageInteraction):
    if not isinstance(inter.component, disnake.Button): return
    if inter.author.bot or inter.author.system: return

    button_custom_id = inter.component.custom_id
    if button_custom_id is None or not button_custom_id.startswith("event_item_lottery"): return
    await inter.response.defer()

    data = button_custom_id.split(":")
    command = data[1]
    lottery_id = int(data[2])

    lottery = await dt_event_item_lottery_repo.get_event_item_lottery(lottery_id)
    if lottery is None:
      await message_utils.delete_message(self.bot, inter.message)
      return await message_utils.generate_error_message(inter, Strings.lottery_button_listener_invalid_lottery)

    is_author = (inter.author.id == int(lottery.author_id)) or (await permissions.is_bot_developer(inter))

    if command == "remove":
      if is_author or (await permissions.has_guild_administrator_role(inter)):
        await message_utils.delete_message(self.bot, inter.message)
        await dt_event_item_lottery_repo.remove_lottery(lottery.id)
        await message_utils.generate_success_message(inter, Strings.lottery_button_listener_removed)
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    elif command == "show":
      if inter.guild is None or str(inter.guild.id) != lottery.guild_id:
        await message_utils.generate_error_message(inter, Strings.unexpected_action)
      else:
        for table in (await items_lottery.generate_guesses_tables(lottery)):
          await inter.send(f"```\n{table}\n```", ephemeral=True, delete_after=60)
          await asyncio.sleep(0.05)
    elif command == "auto_show_guesses":
      if is_author or (await permissions.has_guild_administrator_role(inter)):
        lottery.autoshow_guesses = not lottery.autoshow_guesses
        await run_commit()

        await inter.edit_original_response(components=items_lottery.get_lottery_buttons(lottery))
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    elif command == "repeat":
      if is_author:
        next_event_lottery = await dt_event_item_lottery_repo.get_next_event_item_lottery_by_constrained(int(lottery.author_id), int(lottery.guild_id))
        if next_event_lottery is None:
          message = await inter.original_message()

          author = await lottery.get_author(self.bot)
          if author is not None:
            await items_lottery.handle_closing_lottery_message(self.bot, message, lottery, True)
            await lottery.repeat()
            await items_lottery.create_lottery(author, message, lottery, False)
          else:
            await message_utils.generate_error_message(inter, Strings.lottery_failed_to_get_author)
        else:
          await message_utils.generate_error_message(inter, Strings.lottery_already_created)
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    elif command == "split_rewards":
      if is_author:
        lottery.split_rewards = not lottery.split_rewards
        await run_commit()

        await inter.edit_original_response(components=items_lottery.get_lottery_buttons(lottery))
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    elif command == "auto_repeat":
      if is_author or (await permissions.has_guild_administrator_role(inter)):
        lottery.auto_repeat = not lottery.auto_repeat
        await run_commit()

        await inter.edit_original_response(components=items_lottery.get_lottery_buttons(lottery))
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    elif command == "auto_ping":
      if is_author or (await permissions.has_guild_administrator_role(inter)):
        lottery.autoping_winners = not lottery.autoping_winners
        await run_commit()

        await inter.edit_original_response(components=items_lottery.get_lottery_buttons(lottery))
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    elif command == "refresh":
      if is_author or (await permissions.has_guild_administrator_role(inter)):
        embed = items_lottery.create_lottery_embed(await lottery.get_author(self.bot), lottery)
        await inter.edit_original_response(embed=embed, components=items_lottery.get_lottery_buttons(lottery))
      else:
        await message_utils.generate_error_message(inter, Strings.lottery_button_listener_not_author)
    else:
      await message_utils.generate_error_message(inter, Strings.lottery_button_listener_invalid_command)

  @tasks.loop(hours=24 * config.lotteries.clean_old_lotteries_period_days)
  async def delete_long_closed_lotteries_task(self):
    await self.bot.wait_until_ready()
    lotteries_to_delete = await dt_event_item_lottery_repo.get_lotteries_closed_before_date(datetime.datetime.utcnow() - datetime.timedelta(days=config.lotteries.clean_lotteries_closed_for_more_than_days))

    if lotteries_to_delete:
      logger.info("Starting clearup of old closed lotteries")
      for lottery in lotteries_to_delete:
        await items_lottery.delete_lottery(self.bot, lottery)
        await asyncio.sleep(0.1)
      logger.info(f"Cleared {len(lotteries_to_delete)} old closed lotteries")

  @tasks.loop(time=datetime.time(hour=config.event_tracker.event_start_hour, minute=config.event_tracker.event_start_minute, second=1), count=None)
  async def notify_lottery_closed_task(self):
    await self.bot.wait_until_ready()
    current_datetime = datetime.datetime.utcnow()

    if current_datetime.weekday() == config.event_tracker.event_start_day:
      year, week = dt_helpers.get_event_index(current_datetime)
      lotteries_to_notify = await dt_event_item_lottery_repo.get_active_lotteries(year, week)

      if lotteries_to_notify:
        logger.info("Notifying lotteries are closed")
        for lottery in lotteries_to_notify:
          await items_lottery.lottery_notify_closed_and_waiting(self.bot, lottery)
          await asyncio.sleep(0.05)
        logger.info(f"Notified {len(lotteries_to_notify)} lotteries")

def setup(bot):
  bot.add_cog(DTEventItemLottery(bot))
