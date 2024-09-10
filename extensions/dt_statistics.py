import disnake
from disnake.ext import commands
import io
from typing import Optional
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as mticker
import mplcyberpunk
import datetime
import math

from features.base_cog import Base_Cog
from utils.logger import setup_custom_logger
from config import cooldowns, Strings
from utils import message_utils
from database import dt_statistics_repo, session_maker

logger = setup_custom_logger(__name__)

plt.style.use("cyberpunk")
plt.rc('font', size=14)

async def send_stats(inter: disnake.CommandInteraction, user_data = None, guild_data = None, maximum_data_days_length: Optional[int] = None):
  def process_data_to_dataframe(data):
    dataframe = pd.DataFrame(data, columns=["date", "active", "all"], index=None)

    dataframe = dataframe.set_index(pd.DatetimeIndex(dataframe["date"], name="date")).drop("date", axis=1)
    dataframe = dataframe.resample("D").max().interpolate(limit_direction="backward")
    if maximum_data_days_length is not None:
      total_days = len(dataframe)
      if total_days > maximum_data_days_length:
        new_resample_days_interval = math.ceil(total_days / maximum_data_days_length)
        dataframe = dataframe.resample(f"{new_resample_days_interval}D").mean()

    dataframe["active"] = dataframe["active"].round().astype(int)
    dataframe["all"] = dataframe["all"].round().astype(int)
    dataframe["active_percent"] = dataframe["active"] / dataframe["all"] * 100
    dataframe["all_diff"] = dataframe["all"].diff().fillna(0).astype(int)

    # logger.info(f"\n{dataframe.head(50)}")

    dataframe.reset_index(inplace=True)
    return dataframe

  def generate_graph_file(data, title: str, ylabel: str, all_label: str, all_diff_label: str, active_percent: str, active_label: str, filename: str):
    if data is None: return None

    dataframe = process_data_to_dataframe(data)

    fig, ax1 = plt.subplots(sharex=True, sharey=False)
    fig.subplots_adjust(right=0.85)
    fig.set_size_inches(11.0, 6.0)
    plt.title(title, fontsize=22)
    plt.ylabel(ylabel, fontsize=16)

    ax2 = ax1.twinx()
    ax2.spines.right.set_position(("axes", 1.12))
    ax3 = ax1.twinx()
    ax3.spines.right.set_position(("axes", 1.27))
    ax4 = ax1.twinx()
    ax1.grid(False)
    ax2.grid(False)
    ax3.grid(False)
    ax4.grid(False)

    plot1 = ax1.bar(dataframe.date, dataframe["all"], width=0.8, color="#07e6ec", edgecolor="#07e6ec", label=all_label)
    ax1.set_xticks(ax1.get_xticks(), ax1.get_xticklabels(), rotation=20, ha='right')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.set_major_locator(mticker.MaxNLocator(nbins=6, integer=True, prune="lower"))
    ax1.yaxis.set_major_locator(mticker.MaxNLocator(nbins=10, integer=True))
    ax1.yaxis.set_major_formatter(mticker.ScalarFormatter())
    ax1.tick_params(axis='y', colors=plot1.patches[-1].get_facecolor())
    min_val, max_val = dataframe["all"].values.min(), dataframe["all"].values.max()
    distance = max_val - min_val
    ax1.set_ylim(max(min_val - 0.1 * distance, 0), max_val + 0.1 * distance)

    plot2, = ax2.plot(dataframe.date, dataframe.active_percent, marker="o", color="#f5d300", label=active_percent)
    mplcyberpunk.make_lines_glow(ax2)
    # mplcyberpunk.add_gradient_fill(ax2, 0.5)
    mplcyberpunk.add_underglow(ax2, alpha_underglow=0.2)
    ax2.yaxis.set_major_locator(mticker.MaxNLocator(nbins=10))
    ax2.yaxis.set_major_formatter(mticker.PercentFormatter(decimals=3, xmax=100))
    ax2.tick_params(axis='y', colors=plot2.get_color())
    ax2.get_xaxis().set_visible(False)
    min_val, max_val = dataframe["active_percent"].values.min(), dataframe["active_percent"].values.max()
    distance = max_val - min_val
    ax2.set_ylim(max(min_val - 0.1 * distance, 0), max_val + 0.1 * distance)

    plot3, = ax3.plot(dataframe.date, dataframe.all_diff, marker="o", color="#00ff41", label=all_diff_label)
    mplcyberpunk.make_lines_glow(ax3)
    # mplcyberpunk.add_gradient_fill(ax3, 0.5)
    mplcyberpunk.add_underglow(ax3, alpha_underglow=0.2)
    ax3.yaxis.set_major_locator(mticker.MaxNLocator(nbins=10, integer=True))
    ax3.yaxis.set_major_formatter(mticker.ScalarFormatter())
    ax3.tick_params(axis='y', colors=plot3.get_color())
    ax3.get_xaxis().set_visible(False)
    min_val, max_val = dataframe["all_diff"].values.min(), dataframe["all_diff"].values.max()
    distance = max_val - min_val
    ax3.set_ylim(max(min_val - 0.1 * distance, 0), max_val + 0.1 * distance)

    plot4, = ax4.plot(dataframe.date, dataframe.active, marker="o", color="#f851b7", label=active_label)
    mplcyberpunk.make_lines_glow(ax4)
    # mplcyberpunk.add_gradient_fill(ax4, 0.5)
    mplcyberpunk.add_underglow(ax4, alpha_underglow=0.2)
    ax4.yaxis.set_major_locator(mticker.MaxNLocator(nbins=10, integer=True))
    ax4.yaxis.set_major_formatter(mticker.ScalarFormatter())
    ax4.tick_params(axis='y', colors=plot4.get_color())
    ax4.get_xaxis().set_visible(False)
    min_val, max_val = dataframe["active"].values.min(), dataframe["active"].values.max()
    distance = max_val - min_val
    ax4.set_ylim(max(min_val - 0.1 * distance, 0), max_val + 0.1 * distance)

    fig.legend(handles=[plot1, plot2, plot3, plot4], loc="upper left", fontsize=16, bbox_to_anchor=(0,0,1,1), bbox_transform=ax1.transAxes, frameon=True, facecolor="black", framealpha=0.5, edgecolor="black")

    fig.tight_layout()

    bio = io.BytesIO()
    plt.savefig(bio, transparent=True)

    plt.close(plt.gcf())
    plt.clf()

    bio.seek(0)
    return disnake.File(bio, filename=filename)

  files = []

  if user_data is not None:
    files.append(generate_graph_file(user_data, "User Statistics", "Users", "All Users", "New Users", "Percentage of Active Users", "Active Users", "user_graph.png"))

  if guild_data is not None:
    files.append(generate_graph_file(guild_data, "Guild Statistics", "Guilds", "All Guilds", "New Guilds", "Percentage of Active Guilds", "Active Guilds", "guild_graph.png"))

  if files:
    for file in files:
      await inter.send(file=file)
  else:
    await message_utils.generate_error_message(inter, Strings.public_interface_stats_activity_no_graphs)

class DTStatistics(Base_Cog):
  def __init__(self, bot):
    super(DTStatistics, self).__init__(bot, __file__)

  @commands.slash_command(name="stats")
  async def stats_commands(self, inter: disnake.CommandInteraction):
    pass

  @stats_commands.sub_command_group(name="activity")
  @cooldowns.long_cooldown
  async def activity_stats_commands(self, inter: disnake.CommandInteraction):
    await inter.response.defer(with_message=True)

    if inter.guild is not None:
      if not inter.channel.permissions_for(inter.guild.me).attach_files:
        return await message_utils.generate_error_message(inter, Strings.discord_cant_send_files_to_channel(channel_name=inter.channel.name))

  @activity_stats_commands.sub_command(name="users", description=Strings.public_interface_stats_activity_users_description)
  async def active_user_statistics(self, inter: disnake.CommandInteraction,
                                   days_back: int = commands.Param(default=120, min_value=10, max_value=730)):
    with session_maker() as session:
      statistics_data = await dt_statistics_repo.get_active_user_statistics(session, (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days_back)).date())
      if not statistics_data:
        return await message_utils.generate_error_message(inter, Strings.public_interface_stats_no_data_found)

    await send_stats(inter, user_data=statistics_data)

  @activity_stats_commands.sub_command(name="guilds", description=Strings.public_interface_stats_activity_guilds_description)
  async def active_guild_statistics(self, inter: disnake.CommandInteraction,
                                    days_back: int = commands.Param(default=120, min_value=10, max_value=730)):
    with session_maker() as session:
      statistics_data = await dt_statistics_repo.get_active_guild_statistics(session, (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days_back)).date())
      if not statistics_data:
        return await message_utils.generate_error_message(inter, Strings.public_interface_stats_no_data_found)

    await send_stats(inter, guild_data=statistics_data)

  @activity_stats_commands.sub_command(name="both", description=Strings.public_interface_stats_activity_both_description)
  async def active_both_statistics(self, inter: disnake.CommandInteraction,
                                   days_back: int = commands.Param(default=120, min_value=10, max_value=730)):
    with session_maker() as session:
      statistics_guild_data = await dt_statistics_repo.get_active_guild_statistics(session, (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days_back)).date())
      statistics_user_data = await dt_statistics_repo.get_active_user_statistics(session, (datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=days_back)).date())

      if not statistics_guild_data or not statistics_user_data:
        return await message_utils.generate_error_message(inter, Strings.public_interface_stats_no_data_found)

    await send_stats(inter, user_data=statistics_user_data, guild_data=statistics_guild_data)

def setup(bot):
  bot.add_cog(DTStatistics(bot))
