# Strings separated from code

from features.callable_string import Formatable

class Strings(metaclass=Formatable):
  # Help
  help_description = "Show all message commands and help for them"
  help_name_param_description = "Specify name of command or name of extension as parameter to search help only for thing you want"

  help_slash_command_list_description = "List all slash commands"
  help_slash_command_list_no_slash_commands = "No slash commands registered for this bot"

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
  error_not_found = "Not found\n{code} - {text}"
  error_unknown_error = "Unknown error when processing command, report this to bot administrator"

  # Common
  common_ping_brief = "Ping a bot and get his reponse times"

  common_uptime_brief = "Show uptime of bot"

  common_invite_brief = "Send invite link of the bot"

  # Global Deep Town stuff
  dt_guild_identifier_param_description = "Deep Town Guild identifier"
  dt_user_identifier_param_description = "Deep Town User identifier"
  dt_invalid_identifier = "Invalid identifier entered"
  dt_guild_data_not_found = "Deep Town guild with identifier `{identifier}` not found in database"
  dt_user_profile_no_users = "Deep Town user with identifier `{identifier}` not found in database"

  # Data manager
  data_manager_update_guild_description = "Update data of selected guild in database"
  data_manager_update_guild_get_failed = "Failed to get guild data for guild with identifier `{identifier}`"
  data_manager_update_guild_success = "Data for guild `{guild}` fetched and updated"
  data_manager_update_guild_success_multiple = "Data of {number} guild fetched and updated"

  data_manager_update_all_guilds_description = "Update data of all guilds in database"
  data_manager_update_all_guilds_success_with_periodic_update = "Data update started"
  data_manager_update_all_guilds_success_without_periodic_update = "Updated data of `{guild_num}` guilds"
  data_manager_update_all_guilds_failed_without_periodic_update = "No guilds ids for update from server"

  data_manager_update_tracked_guilds_description = "Update data of tracked guilds in database"
  data_manager_update_tracked_guilds_success = "Updated data of `{guild_num}` guilds"
  data_manager_update_tracked_guilds_failed = "No guilds ids for update from database"

  data_manager_skip_data_update_description = "Skip periodic data update"
  data_manager_skip_data_update_success = "Skipping periodic data update"
  data_manager_skip_data_update_failed = "Periodic data update not running or already marked for skipping"

  data_manager_add_remove_dt_item_name_param_description = "Deep Town item name"

  data_manager_add_dt_item_description = "Create Deep Town item"
  data_manager_add_dt_item_value_param_description = "Event value of one item"
  data_manager_add_dt_item_success = "Set value of item `{name}` to value `{value}`"

  data_manager_remove_dt_item_description = "Remove Deep Town item"
  data_manager_remove_dt_item_success = "Item `{name}` removed from database"
  data_manager_remove_dt_item_failed = "Item `{name}` not found in database"

  data_manager_list_dt_items_description = "List all Deep Town items"
  data_manager_list_dt_items_no_items = "No Deep Town items in database"

  data_manager_set_remove_event_items_year_param_description = "Event year"
  data_manager_set_remove_event_items_week_param_description = "Event week"

  data_manager_set_event_items_description = "Set Deep Town items in event"
  data_manager_set_event_items_item_name_param_description = "Event Deep Town Item {number}"
  data_manager_set_event_items_item_amount_param_description = "Base amount for item {number}"
  data_manager_set_event_items_item_not_in_database = "Item `{item}` not found in database"
  data_manager_set_event_items_success = "Items for event `{event_year} {event_week}` set\n{item1} - {base_amount1}\n{item2} - {base_amount2}\n{item3} - {base_amount3}\n{item4} - {base_amount4}"
  data_manager_set_event_items_repeated_items = "Inserted not unique items"

  data_manager_remove_event_items_description = "Remove Deep Town items for event"
  data_manager_remove_event_items_success = "Removed event items for `{event_year} {event_week}`"
  data_manager_remove_event_items_failed = "Can't find event items for `{event_year} {event_week}`"

  data_manager_load_data_description = "Load manually event data"
  data_manager_load_data_no_attachments = "No attachments present"
  data_manager_load_data_loading_started = "Data loading started"
  data_manager_load_data_loaded = "New data loaded, `{count}` rows\nIf some data are missing then file was in invalid format or data keys were missing"

  data_manager_dump_guild_participation_data_description = "Dump Deep Town guild event participation data"
  data_manager_dump_guild_participation_data_no_data = "No data found for guild with id `{guild_id}`"
  data_manager_dump_guild_participation_data_no_data_no_guild_id = "No data found"
  data_manager_dump_guild_participation_data_success = "Dump created"

  # Event Tracker
  event_report_announcer_add_or_modify_tracker_description = "Add guild for tracking or modify existing announcement channel"
  event_report_announcer_add_or_modify_tracker_tracker_limit_reached = "Tracker limit ({limit} per guild) reached"
  event_report_announcer_add_or_modify_tracker_success_with_channel = "Set tracking for guild `{guild}` and announcement to channel `{channel}`"
  event_report_announcer_add_or_modify_tracker_announce_channel_param_description = "Channel for announcing results at the end of event"

  event_report_announcer_remove_tracker_description = "Remove event tracker and its announcement settings"
  event_report_announcer_remove_tracker_success = "Removed tracking for guild `{guild}`"
  event_report_announcer_remove_tracker_failed = "Can't find tracking settings for guild with identifier `{identifier}`"

  event_report_announcer_list_trackers_description = "List all active trackers for this discord guild"
  event_report_announcer_list_trackers_no_trackers = "No trackers found"

  event_report_announcer_generate_announcements_description = "Generate announcements for tracked guild by current discord guild"
  event_report_announcer_generate_announcements_no_data = "No data found"
  event_report_announcer_generate_announcements_success = "Announcements generated"

  event_report_announcer_guild_report_description = "Generate Deep Town guild report"

  # Public interface
  public_interface_guild_report_description = "Generate report for specific Deep Town guild"
  public_interface_guild_report_tight_format_param_description = "Tight format of table (default: False)"

  public_interface_guild_participations_description = "Guild event participations"

  public_interface_guild_members_description = "List current members of specific Deep Town guild"

  public_interface_guild_leaderboard_description = "Leaderboard of guilds by level (if multiple guild have same level then sorted by name)"
  public_interface_guild_leaderboard_no_guilds = "No guilds found in database"

  public_interface_guild_profile_description = "Show Deep Town guild profile"
  public_interface_guild_profile_no_guilds = "No guilds found for guild identifier `{identifier}`"

  public_interface_user_profile_description = "Show Deep Town user profile"

  public_interface_user_event_participations_description = "User event participations"

  public_interface_event_help_description = "Show items for current item"
  public_interface_event_help_no_items = "Items not set for this event"

  public_interface_event_leaderboard_current_description = "Show leaderboard of participants in current event"
  public_interface_event_leaderboard_current_user_count_param_description = "Number of top users to display"

  public_interface_event_leaderboard_specific_description = "Show leaderboard of participants in specific event"
  public_interface_event_leaderboard_specific_year_param_description = "Year of event"
  public_interface_event_leaderboard_specific_week_param_description = "Week of event"
  public_interface_event_leaderboard_specific_user_count_param_description = "Number of top users to display"

  public_interface_delete_bot_message_invalid_message = "This is not message of this bot!"

  # Blacklist
  blacklist_type_param_description = "Blacklist type"
  blacklist_identifier_param_description = "Identifier of subject"

  blacklist_add_description = "Add subject to blacklist"
  blacklist_add_invalid_identifier = "Invalid identifier entered"
  blacklist_add_already_on_blacklist = "This subject is already on blacklist"
  blacklist_add_invalid_type = "Invalid blacklist type"
  blacklist_add_subject_not_found = "Subject is not in database"
  blacklist_add_success = "Subject `{subject_name}` of type `{type}` added to blacklist and removed from records"

  blacklist_remove_description = "Remove subject from blacklist"
  blacklist_remove_success = "Removed subject with identifier `{identifier}` of type `{type}` from blacklist"
  blacklist_remove_failed = "Subject with identifier `{identifier}` of type `{type}` is not on blacklist"

  blacklist_list_description = "List all subjects on blacklist"

  blacklist_report_cheater_description = "Report user cheater to bot administrator"
  blacklist_report_cheater_invalid_report_type = "Invalid report type"
  blacklist_report_identifier_param_description = "Identifier of entity to report"
  blacklist_report_reason_param_description = "Optional reason why you think this entity is cheating"
  blacklist_report_report_channel_not_found = "Report channel not found, unable to report cheater"
  blacklist_report_success = "Report submited"
  blacklist_report_user_cheater_user_not_found = "User not found in database"
  blacklist_report_guild_cheater_guild_not_found = "Guild not found in database"
