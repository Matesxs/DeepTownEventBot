import disnake
from disnake.ext import commands
import datetime
import humanize
from typing import List, Union, Optional
from tabulate import tabulate
import statistics

from utils import string_manipulation
from utils.dt_helpers import DTGuildData
from database.event_participation_repo import EventParticipation

def generate_text_guild_report(guild_data: DTGuildData, event_year: int, event_week: int, colms: Optional[List[str]]=None) -> List[str]:
  guild_data.players.sort(key=lambda x: x.last_event_contribution, reverse=True)

  if colms is None:
    colms = ["No°", "Name", "Level", "Donate"]

  current_time = datetime.datetime.utcnow()
  contributions = []
  data_list = []

  for idx, participant in enumerate(guild_data.players):
    data = []
    if "No°" in colms:
      data.append(idx + 1)
    if "Name" in colms:
      data.append(participant.name)
    if "ID" in colms:
      data.append(participant.id)
    if "Level" in colms:
      data.append(participant.level)
    if "Depth" in colms:
      data.append(participant.depth)
    if "Online" in colms:
      data.append(humanize.naturaltime(current_time - participant.last_online) if participant.last_online is not None else "Never")
    if "Donate" in colms:
      data.append(participant.last_event_contribution)

    data_list.append(data)
    contributions.append(participant.last_event_contribution)

  description = f"{guild_data.name} - ID: {guild_data.id} - Level: {guild_data.level}\nYear: {event_year} Week: {event_week}\nDonate - Median: {statistics.median(contributions):.2f} Average: {statistics.mean(contributions):.2f}, Total: {sum(contributions)}\n\n"
  table_strings = (description + tabulate(data_list, colms, tablefmt="github")).split("\n")

  announce_strings = []
  while table_strings:
    final_string, table_strings = string_manipulation.add_string_until_length(table_strings, 1900, "\n")
    announce_strings.append(f"```py\n{final_string}\n```")

  return announce_strings

async def send_text_guild_report(report_channel: Union[disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable, disnake.CommandInteraction, commands.Context], guild_data: DTGuildData, event_year: int, event_week: int, colms: Optional[List[str]]=None):
  strings = generate_text_guild_report(guild_data, event_year, event_week, colms)
  for string in strings:
    await report_channel.send(string)


def generate_participations_page_strings(participations: List[EventParticipation], include_guild: bool=False) -> List[str]:
  participation_data = [((participation.event_year, participation.event_week, participation.dt_guild.name, participation.amount) if include_guild else (participation.event_year, participation.event_week, participation.amount)) for participation in participations]
  participation_table_lines = tabulate(participation_data, ["Year", "Week", "Guild", "Donate"] if include_guild else ["Year", "Week", "Donate"], tablefmt="github").split("\n")

  output_pages = []
  while participation_table_lines:
    data_string, participation_table_lines = string_manipulation.add_string_until_length(participation_table_lines, 1500, "\n")
    output_pages.append(data_string)

  return output_pages
