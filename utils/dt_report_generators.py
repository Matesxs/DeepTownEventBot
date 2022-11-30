import disnake
from disnake.ext import commands
import datetime
import humanize
from typing import List, Union, Optional
from tabulate import tabulate
import statistics

from utils import string_manipulation
from utils.dt_helpers import DTGuildData

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