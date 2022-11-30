# Strings separated from code

from features.callable_string import Formatable

class Strings(metaclass=Formatable):
  # Help
  help_description = "Show all message commands and help for them"
  help_name_param_description = "Specify name of command or name of extension as parameter to search help only for thing you want"

  help_commands_list_description = "Show list of all available message commands"

  # System
  system_load_description = "Load unloaded extension"
  system_unable_to_load_cog = "Unable to load `{cog}` extension\n`{e}`"
  system_cog_loaded = "Extension `{extension}` loaded"

  system_unload_description = "Unload loaded extension"
  system_unload_protected_cog = "Unable to unload `{extension}` extension - protected"
  system_unable_to_unload_cog = "Unable to unload `{cog}` extension\n`{e}`"
  system_cog_unloaded = "Extension `{extension}` unloaded"

  system_reload_description = "Reload loaded extension"
  system_unable_to_reload_cog = "Unable to reload `{cog}` extension\n`{e}`"
  system_cog_reloaded = "Extension `{extension}` reloaded"

  system_cog_not_found = "Extension `{extension}` not found in extension folders"

  system_cogs_description = "Show all extensions and their states"

  system_logout_brief = "Turn off bot"

  # Errors
  error_command_syntax_error = "Unknown syntax of command"
  error_unknown_command = "Unknown command - use /help for help"
  error_command_on_cooldown = "This command is on cooldown. Please wait {remaining}s"
  error_missing_permission = "You do not have the permissions to use this command."
  error_missing_role = "You do not have {role} role to use this command"
  error_missing_argument = "Missing {argument} argument of command\n{signature}"
  error_bad_argument = "Some arguments of command missing or wrong, use /help to get more info"
  error_max_concurrency_reached = "Bot is busy, try it later"
  error_no_private_message = "This command can't be used in private channel"
  error_interaction_timeout = "Interaction took more than 3 seconds to be responded to. Try again later."
  error_forbiden = "Bot can't do this action"
  error_blocked_dms = "You have blocked DMs"

  # Common
  common_ping_brief = "Ping a bot and get his reponse times"

  common_uptime_brief = "Show uptime of bot"

  common_invite_brief = "Send invite link of the bot"

  # Data manager
  data_manager_update_guild_description = "Update data of selected guild in database"
  data_manager_update_guild_get_failed = "Failed to get guild data"
  data_manager_update_guild_success = "Data for guild `{guild}` fetched and updated"

  data_manager_update_all_guilds_description = "Update data of all guilds in database"
  data_manager_update_all_guilds_success = "Updated data of `{guild_num}` guilds"
  data_manager_update_all_guilds_failed = "No guilds ids for update from server"

  data_manager_update_tracked_guilds_description = "Update data of tracked guilds in database"
  data_manager_update_tracked_guilds_success = "Updated data of `{guild_num}` guilds"
  data_manager_update_tracked_guilds_failed = "No guilds ids for update from database"

  data_manager_skip_data_update_description = "Skip periodic data update"
  data_manager_skip_data_update_success = "Skipping periodic data update"
  data_manager_skip_data_update_failed = "Periodic data update not running or already marked for skipping"

  data_manager_load_data_description = "Load manually event data"
  data_manager_load_data_loaded = "New data loaded, `{count}` rows\nIf some data are missing then file was in invalid format or data keys were missing"

  data_manager_dump_guild_participation_data_description = "Dump Deep Town guild event participation data"
  data_manager_dump_guild_participation_data_no_data = "No data found for guild with id `{guild_id}`"
  data_manager_dump_guild_participation_data_success = "Dump created"

  # Event Tracker
  public_interface_guild_data_not_found = "No data found"

  event_data_tracker_add_or_modify_tracker_description = "Add guild for tracking or modify existing announcement channel"
  event_data_tracker_add_or_modify_tracker_failed_to_get_data = "Failed to get guild data"
  event_data_tracker_add_or_modify_tracker_tracker_limit_reached = "Tracker limit ({limit} per guild) reached"
  event_data_tracker_add_or_modify_tracker_success_with_channel = "Set tracking for guild `{guild}` and announcement to channel `{channel}`"
  event_data_tracker_add_or_modify_tracker_success_without_channel = "Set tracking for guild `{guild}`"

  event_data_tracker_remove_tracker_description = "Remove event tracker and its announcement settings"
  event_data_tracker_remove_tracker_success = "Removed tracking for guild `{guild}`"
  event_data_tracker_remove_tracker_failed = "Can't find tracking settings for guild with id `{guild_id}`"

  event_data_tracker_list_trackers_description = "List all active trackers for this discord guild"
  event_data_tracker_list_trackers_no_trackers = "No trackers found"

  event_data_tracker_generate_announcements_description = "Generate announcements for tracked guild by current discord guild"
  event_data_tracker_generate_announcements_no_data = "No data found"
  event_data_tracker_generate_announcements_success = "Announcements generated"

  event_data_tracker_guild_report_description = "Generate Deep Town guild report"

  # Public interface
  public_interface_guild_report_description = "Generate report for specific Deep Town guild"

  public_interface_guild_members_description = "List current members of specific Deep Town guild"

  public_interface_search_guilds_description = "List Deep Town guilds or find specific one"
