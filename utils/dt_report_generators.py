import disnake
from disnake.ext import commands
import datetime
import humanize
from typing import List, Union
from tabulate import tabulate

from utils import string_manipulation
from database import event_participation_repo
from utils.dt_helpers import DTGuildData

def generate_text_guild_report(guild_data: DTGuildData, event_year: int, event_week: int, detailed: bool=False) -> List[str]:
  guild_data.players.sort(key=lambda x: x.last_event_contribution, reverse=True)

  part_stats = event_participation_repo.get_participation_stats_for_guild_and_event(guild_data.id, event_year, event_week)
  description = f"{guild_data.name} - ID: {guild_data.id} - Level: {guild_data.level}\nYear: {event_year} Week: {event_week}\nAverage participation: {part_stats[0]:.2f}, Total participation: {int(part_stats[1])}\n\n"
  headers = ["No°", "Name", "ID", "Level", "Depth", "Online", "Donate"] if detailed else ["No°", "Name", "Level", "Donate"]
  data_list = []

  current_time = datetime.datetime.utcnow()
  for idx, participant in enumerate(guild_data.players):
    if detailed:
      data_list.append((idx + 1, participant.name, participant.id, participant.level, participant.depth, humanize.naturaltime(current_time - participant.last_online) if participant.last_online is not None else "Never", participant.last_event_contribution))
    else:
      data_list.append((idx + 1, participant.name, participant.level, participant.last_event_contribution))

  table_strings = (description + tabulate(data_list, headers, tablefmt="github")).split("\n")

  announce_strings = []
  while table_strings:
    final_string, table_strings = string_manipulation.add_string_until_length(table_strings, 1900, "\n")
    announce_strings.append(f"```py\n{final_string}\n```")

  return announce_strings

async def send_text_guild_report(report_channel: Union[disnake.TextChannel, disnake.Thread, disnake.VoiceChannel, disnake.PartialMessageable, disnake.CommandInteraction, commands.Context], guild_data: DTGuildData, event_year: int, event_week: int, detailed: bool=False):
  strings = generate_text_guild_report(guild_data, event_year, event_week, detailed)
  for string in strings:
    await report_channel.send(string)