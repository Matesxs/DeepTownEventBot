import disnake
from disnake.ext import commands
import datetime
import humanize
from typing import List, Union, Optional
from table2ascii import table2ascii, Alignment
import statistics

from utils import string_manipulation
from database.tables.event_participation import EventParticipation
from database.tables.dt_guild import DTGuild

def generate_participation_strings(participations: List[EventParticipation], colms: List[str], colm_padding: int=0) -> List[str]:
  current_time = datetime.datetime.utcnow()
  data_list = []
  alligments = []

  if "No°" in colms:
    alligments.append(Alignment.RIGHT)
  if "Year" in colms:
    alligments.append(Alignment.RIGHT)
  if "Week" in colms:
    alligments.append(Alignment.RIGHT)
  if "Guild" in colms:
    alligments.append(Alignment.LEFT)
  if "Name" in colms:
    alligments.append(Alignment.LEFT)
  if "ID" in colms:
    alligments.append(Alignment.RIGHT)
  if "Level" in colms:
    alligments.append(Alignment.RIGHT)
  if "Depth" in colms:
    alligments.append(Alignment.RIGHT)
  if "Online" in colms:
    alligments.append(Alignment.LEFT)
  if "Donate" in colms:
    alligments.append(Alignment.RIGHT)

  for idx, participation in enumerate(participations):
    data = []
    if "No°" in colms:
      data.append(idx + 1)
    if "Year" in colms:
      data.append(participation.event_year)
    if "Week" in colms:
      data.append(participation.event_week)
    if "Guild" in colms:
      data.append(participation.dt_guild.name)
    if "Name" in colms:
      data.append(participation.dt_user.username)
    if "ID" in colms:
      data.append(participation.dt_user_id)
    if "Level" in colms:
      data.append(participation.dt_user.level)
    if "Depth" in colms:
      data.append(participation.dt_user.depth)
    if "Online" in colms:
      data.append(humanize.naturaltime(current_time - participation.dt_user.last_online) if participation.dt_user.last_online is not None else "Never")
    if "Donate" in colms:
      data.append(participation.amount)

    data_list.append(data)

  return table2ascii(body=data_list, header=colms, alignments=alligments, cell_padding=colm_padding, first_col_heading="No°" in colms).split("\n")

async def send_text_guild_event_participation_report(report_channel: Union[disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable, disnake.CommandInteraction, commands.Context], guild: DTGuild, participations: List[EventParticipation], colms: Optional[List[str]]=None, colm_padding: int=0):
  if not participations: return
  if colms is None:
    colms = ["No°", "Name", "Level", "Donate"]

  participation_amounts = [p.amount for p in participations]
  if not participation_amounts: participation_amounts = [0]
  description_strings = f"{guild.name} - ID: {guild.id} - Level: {guild.level}\nYear: {participations[0].event_year} Week: {participations[0].event_week}\nDonate - Median: {statistics.median(participation_amounts):.2f} Average: {statistics.mean(participation_amounts):.2f}, Total: {sum(participation_amounts)}\n".split("\n")

  strings = [*description_strings]
  strings.extend(generate_participation_strings(participations, colms, colm_padding))

  announce_strings = []
  while strings:
    final_string, strings = string_manipulation.add_string_until_length(strings, 1900, "\n")
    announce_strings.append(f"```py\n{final_string}\n```")

  for announce_string in announce_strings:
    await report_channel.send(announce_string)

def generate_participations_page_strings(participations: List[EventParticipation], include_guild: bool=False) -> List[str]:
  header = ["Year", "Week", "Guild", "Donate"] if include_guild else ["Year", "Week", "Donate"]
  participation_table_lines = generate_participation_strings(participations, header, 1)

  output_pages = []
  while participation_table_lines:
    data_string, participation_table_lines = string_manipulation.add_string_until_length(participation_table_lines, 1500, "\n")
    output_pages.append(data_string)

  return output_pages
