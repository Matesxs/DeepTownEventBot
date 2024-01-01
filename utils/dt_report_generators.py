import disnake
from disnake.ext import commands
import datetime
import humanize
from typing import List, Union, Optional
from table2ascii import table2ascii, Alignment
import statistics
import pandas as pd
import io

from utils import string_manipulation, dt_helpers
from database.tables.event_participation import EventParticipation, EventSpecification
from database.tables.dt_guild import DTGuild

def generate_participation_strings(participations: List[EventParticipation], colms: List[str], colm_padding: int=0) -> List[str]:
  current_time = datetime.datetime.utcnow()
  data_list = []
  alligments = []
  sorted_colms = []

  if "No°" in colms:
    alligments.append(Alignment.RIGHT)
    sorted_colms.append("No°")
  if "Year" in colms:
    alligments.append(Alignment.RIGHT)
    sorted_colms.append("Year")
  if "Week" in colms:
    alligments.append(Alignment.RIGHT)
    sorted_colms.append("Week")
  if "Guild" in colms:
    alligments.append(Alignment.LEFT)
    sorted_colms.append("Guild")
  if "Name" in colms:
    alligments.append(Alignment.LEFT)
    sorted_colms.append("Name")
  if "ID" in colms:
    alligments.append(Alignment.RIGHT)
    sorted_colms.append("ID")
  if "Level" in colms:
    alligments.append(Alignment.RIGHT)
    sorted_colms.append("Level")
  if "Depth" in colms:
    alligments.append(Alignment.RIGHT)
    sorted_colms.append("Depth")
  if "Online" in colms:
    alligments.append(Alignment.LEFT)
    sorted_colms.append("Online")
  if "Donate" in colms:
    alligments.append(Alignment.RIGHT)
    sorted_colms.append("Donate")
  if "Standing" in colms:
    alligments.append(Alignment.LEFT)
    sorted_colms.append("Standing")

  participation_amounts = [p.amount for p in participations]
  average_participation = statistics.mean(participation_amounts) if participation_amounts else 0
  participation_spread = max(participation_amounts) - min(participation_amounts)
  high_average_participation = average_participation + participation_spread * 0.1
  low_average_participation = average_participation - participation_spread * 0.1

  for idx, participation in enumerate(participations):
    data = []
    if "No°" in colms:
      data.append(idx + 1)
    if "Year" in colms:
      data.append(participation.event_specification.event_year)
    if "Week" in colms:
      data.append(participation.event_specification.event_week)
    if "Guild" in colms:
      data.append(string_manipulation.truncate_string(participation.dt_guild.name, 20))
    if "Name" in colms:
      data.append(string_manipulation.truncate_string(participation.dt_user.username, 20))
    if "ID" in colms:
      data.append(participation.dt_user_id)
    if "Level" in colms:
      data.append(participation.dt_user.level)
    if "Depth" in colms:
      data.append(participation.dt_user.depth)
    if "Online" in colms:
      data.append(humanize.naturaltime(current_time - participation.dt_user.last_online) if participation.dt_user.last_online is not None else "*Never*")
    if "Donate" in colms:
      data.append(string_manipulation.format_number(participation.amount))
    if "Standing" in colms:
      if participation.amount < low_average_participation or participation.amount == 0:
        data.append("Low")
      elif participation.amount > high_average_participation:
        data.append("High")
      else:
        data.append("Average")

    data_list.append(data)

  return table2ascii(body=data_list, header=sorted_colms, alignments=alligments, cell_padding=colm_padding, first_col_heading="No°" in colms).split("\n")

async def send_text_guild_event_participation_report(output: Union[disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable, disnake.ApplicationCommandInteraction, commands.Context, disnake.Message], guild: DTGuild, participations: List[EventParticipation], colms: Optional[List[str]]=None, colm_padding: int=1, show_event_items: bool=True):
  if not participations: return
  if colms is None:
    colms = ["No°", "Name", "Level", "Donate"]

  participation_amounts = [p.amount for p in participations]
  non_zero_participation_amounts = [p for p in participation_amounts if p > 0]
  all_players = len(participation_amounts)
  active_players = len([a for a in participation_amounts if a > 0])

  if not participation_amounts: participation_amounts = [0]
  if not non_zero_participation_amounts: non_zero_participation_amounts = [0]

  event_items_table = get_event_items_table(participations[0].event_specification, colm_padding=colm_padding)
  start_date, end_date = dt_helpers.event_index_to_date_range(participations[0].event_specification.event_year, participations[0].event_specification.event_week)

  description_strings = (f"{guild.name} - ID: {guild.id} - Level: {guild.level}\nYear: {participations[0].event_specification.event_year} Week: {participations[0].event_specification.event_week}\n{start_date.day}.{start_date.month}.{start_date.year} - {end_date.day}.{end_date.month}.{end_date.year}\n" +
                         (("\nEvent items:\n" + event_items_table + "\n\n") if show_event_items and event_items_table is not None else "") +
                         f"Donate - Median: {string_manipulation.format_number(statistics.median(non_zero_participation_amounts), 3)} Average: {string_manipulation.format_number(statistics.mean(participation_amounts), 3)}, Total: {string_manipulation.format_number(sum(participation_amounts), 3)}\nActivity: {active_players}/{all_players}\n").split("\n")

  strings = [*description_strings]
  strings.extend(generate_participation_strings(participations, colms, colm_padding))

  announce_strings = []
  while strings:
    final_string, strings = string_manipulation.add_string_until_length(strings, 1900, "\n")
    announce_strings.append(f"```\n{final_string}\n```")

  if announce_strings:
    if isinstance(output, disnake.Message):
      await output.edit(announce_strings[0], embeds=[], components=None)

      for announce_string in announce_strings[1:]:
        await output.channel.send(announce_string)
    else:
      for announce_string in announce_strings:
        await output.send(announce_string)

async def send_csv_guild_event_participation_report(output: Union[disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable, disnake.ApplicationCommandInteraction, commands.Context, disnake.Message], guild: DTGuild, participations: List[EventParticipation]):
  if not participations: return

  data = [(participation.dt_user.username, participation.amount) for participation in participations]
  dataframe = pd.DataFrame(data, columns=["Name", "Donate"])

  ioBuffer = io.BytesIO()
  ioBuffer.write(bytes(dataframe.to_csv(index=False), encoding='utf-8'))
  ioBuffer.seek(0)

  start_date, end_date = dt_helpers.event_index_to_date_range(participations[0].event_specification.event_year, participations[0].event_specification.event_week)
  await output.send(file=disnake.File(ioBuffer, filename=f"Donate__{guild.name}__{start_date.day}.{start_date.month}.{start_date.year}_{end_date.day}.{end_date.month}.{end_date.year}.csv"))

def generate_participations_page_strings(participations: List[EventParticipation]) -> List[str]:
  participation_table_lines = generate_participation_strings(participations, ["Year", "Week", "Guild", "Donate"], 1)

  output_pages = []
  while participation_table_lines:
    data_string, participation_table_lines = string_manipulation.add_string_until_length(participation_table_lines, 1200, "\n")
    output_pages.append(data_string)

  return output_pages

def get_event_items_table(event_specification: EventSpecification, colm_padding: int=1, only_names: bool=False) -> Optional[str]:
  if event_specification is None: return None
  if not event_specification.participation_items: return None

  if not only_names:
    event_items_data = [(string_manipulation.truncate_string(eitem.item.name, 20),
                         f"{string_manipulation.format_number(eitem.item.value, 2)}",
                         f"{string_manipulation.format_number(eitem.item.value / eitem.item.cumulative_crafting_time_per_item, 2) if eitem.item.cumulative_crafting_time_per_item > 0 else '-'}")
                        for eitem in event_specification.participation_items]
    return table2ascii(["Name", "Value", "Value/s"], event_items_data, alignments=[Alignment.LEFT, Alignment.RIGHT, Alignment.RIGHT], cell_padding=colm_padding)

  event_items_data = [(string_manipulation.truncate_string(eitem.item.name, 20), ) for eitem in event_specification.participation_items]
  return table2ascii(["Event items"], event_items_data, alignments=[Alignment.LEFT], cell_padding=colm_padding)

def get_event_items_scaling_table(event_specification: EventSpecification, levels: int=30, colm_padding: int=1) -> Optional[str]:
  if event_specification is None: return None
  if not event_specification.participation_items: return None

  event_items = [ei for ei in event_specification.participation_items if ei.base_amount is not None]
  if not event_items: return None

  colm_names = ["Level", *[string_manipulation.truncate_string(ei.item.name, 20) for ei in event_items]]
  scaling_data = [(idx + 1, *scalings) for idx, scalings in enumerate(zip(*[ei.get_event_amount_scaling(levels=levels) for ei in event_items]))]

  return table2ascii(colm_names, scaling_data, alignments=[Alignment.RIGHT] * len(colm_names), cell_padding=colm_padding, first_col_heading=True, footer=["Sum", *[ei.get_event_amount_sum(levels=levels) for ei in event_items]])
