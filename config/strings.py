# Strings separated from code

from features.callable_string import Formatable

class Strings(metaclass=Formatable):
  # Global
  discord_text_channel_param_description = "Guild text channel"
  discord_cant_send_message_to_channel = "Cant send messages to channel `{channel_name}`"
  discord_cant_send_files_to_channel = "Cant send files to channel `{channel_name}`"
  unexpected_action = "You shouldn't be able to do this!"

  # Help
  help_description = "Show all commands and help for them"

  # System
  system_status_messages_set_description = "Set list of status messages"

  system_status_messages_set_with_default_description = "Extend default list of status messages"

  system_status_messages_set_success = "Status messages set"
  system_status_messages_status_messages_param_description = "Status messages separated by `;`"

  system_status_messages_reset_description = "Reset status messages to default messages from config"
  system_status_messages_reset_success = "Status messages reset to default"

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

  system_logout_description = "Turn off bot"

  system_update_description = "Pull latest version of bot from git repository and logout bot"
  system_update_already_up_to_date = "Bot is already up to date"

  system_git_pull_description = "Pull latest version of bot from git repository"

  # Errors
  error_command_syntax_error = "Unknown syntax of command"
  error_unknown_command = "Unknown command - use /help for help"
  error_command_on_cooldown = "This command is on cooldown. Please wait {remaining}s"
  error_not_guild_owner = "You are not owner of this guild"
  error_not_administrator = "You are not administrator of this guild"
  error_not_administrator_and_not_set = "You are owner or administrator of this guild because your guild don't have administrator role set"
  not_administrator_role_set = "Your guild dont have set administrator role"
  error_not_owner = "You are not owner of this bot"
  error_not_developer = "You are not developer of this bot"
  error_missing_permission = "You do not have the permissions to use this command"
  error_bot_missing_permission = "Bot don't have permission to do this action"
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

  # Discord manager
  discord_manager_get_guilds_description = "Get list of guild in which is bot connected"
  discord_manager_get_guilds_message = "**Guild List**\n```\n{message}\n```"

  discord_manager_pull_data_description = "Pull discord informations to database"
  discord_manager_pull_data_success = "Data pulled"

  # Common
  common_ping_description = "Ping a bot and get his reponse times"

  common_uptime_description = "Show uptime of bot"

  common_invite_description = "Send invite link of the bot"

  # Global Deep Town stuff
  dt_guild_identifier_param_description = "Deep Town Guild identifier"
  dt_user_identifier_param_description = "Deep Town User identifier"
  dt_invalid_identifier = "Invalid identifier entered"
  dt_guild_not_found = "Deep Town guild with identifier `{identifier}` not found in database"
  dt_user_not_found = "Deep Town user with identifier `{identifier}` not found in database"
  dt_event_data_not_found = "Not found event data for event `{year}` `{week}`"
  dt_event_identifier_param_description = "Event identificator in format 'Event_year Event_week'"

  # Static data manager
  static_data_manager_add_dt_item_description = "Create Deep Town item"
  static_data_manager_add_dt_item_type_param_description = "Type of item"
  static_data_manager_add_dt_item_source_param_description = "Source of item"
  static_data_manager_add_dt_item_value_param_description = "Event value of one item"
  static_data_manager_add_dt_item_crafting_time_param_description = "Crafting time of item if craftable"
  static_data_manager_add_dt_item_crafting_batch_size_param_description = "Number of crafted items per batch if craftable"
  static_data_manager_add_dt_item_success_craftable = "Set item `{item_type}` `{name}` to value `{value}` and crafting time `{crafting_time}`"
  static_data_manager_add_dt_item_success_noncraftable = "Set item `{item_type}` `{name}` to value `{value}`"

  static_data_manager_remove_dt_item_description = "Remove Deep Town item"
  static_data_manager_remove_dt_item_success = "Item `{name}` removed from database"
  static_data_manager_remove_dt_item_failed = "Item `{name}` not found in database"

  static_data_manager_add_remove_dt_item_name_param_description = "Deep Town item name"

  static_data_manager_list_dt_items_description = "List all Deep Town items"
  static_data_manager_list_dt_items_no_items = "No Deep Town items in database"

  static_data_manager_target_item_not_found = "Target item not found in database"

  static_data_manager_modify_dt_item_component_description = "Modify component of item"
  static_data_manager_modify_dt_item_component_target_item_param_description = "Item for which modify component"
  static_data_manager_modify_dt_item_component_component_item_param_description = "Item component"
  static_data_manager_modify_dt_item_component_amount_param_description = "Number of components to craft target item (0 to remove) (can be floating point)"
  static_data_manager_modify_dt_item_component_target_not_craftable = "Target item is not craftable"
  static_data_manager_modify_dt_item_component_component_not_found = "Component item not found in database"
  static_data_manager_modify_dt_item_component_removed = "Removed `{component_item}` as component of `{target_item}`"
  static_data_manager_modify_dt_item_component_remove_failed = "Component `{component_item}` is not component of `{target_item}`"
  static_data_manager_modify_dt_item_component_added = "Added `{amount}x {component_item}` as component of `{target_item}`"

  static_data_manager_remove_dt_item_components_description = "Remove all components of item"
  static_data_manager_remove_dt_item_components_target_item_param_description = "Item for which remove components"
  static_data_manager_remove_dt_item_components_removed = "Removed all components of `{target_item}`"
  static_data_manager_remove_dt_item_components_failed = "Target item `{target_item}` have no components"

  # Data manager
  data_manager_update_guild_description = "Update data of selected guild in database"
  data_manager_update_guild_get_failed = "Failed to get guild data for guild with identifier `{identifier}`"
  data_manager_update_guild_success = "Data for guild `{guild}` fetched and updated"

  data_manager_update_all_guilds_description = "Update data of all guilds in database"
  data_manager_update_all_guilds_success_with_periodic_update = "Data update started"
  data_manager_update_all_guilds_success_without_periodic_update = "Updated data of `{guild_num}` guilds"
  data_manager_update_all_guilds_failed_without_periodic_update = "No guilds ids for update from server"

  data_manager_update_tracked_guilds_description = "Update data of tracked guilds in database"
  data_manager_update_tracked_guilds_success = "Updated data of `{guild_num}` guilds"
  data_manager_update_tracked_guilds_failed = "No guilds ids for update from database"

  data_manager_set_event_items_description = "Set Deep Town items in event"
  data_manager_set_event_items_current_level_param_description = "Current level of event"
  data_manager_set_event_items_item_name_param_description = "Event Deep Town Item {number}"
  data_manager_set_event_items_item_amount_param_description = "Base amount for item {number}"
  data_manager_set_event_items_update_items_lotteries_param_description = "Update lotteries after setting event items"
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
  data_manager_dump_guild_participation_data_no_data = "No data found for guild with id `{identifier}`"
  data_manager_dump_guild_participation_data_no_data_no_guild_id = "No data found"
  data_manager_dump_guild_participation_data_success = "Dump created"

  # Event Tracker
  event_report_announcer_add_or_modify_tracker_description = "Add guild for tracking or modify existing announcement channel"
  event_report_announcer_add_or_modify_tracker_no_channels_set = "No channels specified for reporting"
  event_report_announcer_add_or_modify_tracker_tracker_limit_reached = "Tracker limit ({limit} per guild) reached"
  event_report_announcer_add_or_modify_tracker_success_with_channel = "Set tracking for guild `{guild}`, text announcement to channel `{channel1}` and csv announcement to channel `{channel2}`"

  event_report_announcer_remove_tracker_description = "Remove event tracker and its announcement settings"
  event_report_announcer_remove_tracker_success = "Removed tracking for guild `{guild}`"
  event_report_announcer_remove_tracker_failed = "Can't find tracking settings for guild with identifier `{identifier}`"

  event_report_announcer_list_trackers_description = "List all active trackers for this discord guild"
  event_report_announcer_list_trackers_no_trackers = "No trackers found"

  event_report_announcer_guild_report_description = "Generate Deep Town guild report"

  # Public interface
  public_interface_guild_report_description = "Generate report for specific Deep Town guild"
  public_interface_guild_report_tight_format_param_description = "Tight format of table (default: False)"

  public_interface_csv_guild_report_description = "Generate CSV report for specific Deep Town guild"

  public_interface_guild_participations_description = "Guild event participations"

  public_interface_guild_leaderboard_description = "Leaderboard of guilds by level (if multiple guild have same level then sorted by name)"
  public_interface_guild_leaderboard_no_guilds = "No guilds found in database"

  public_interface_guild_profile_description = "Show Deep Town guild profile"
  public_interface_guild_profile_no_guilds = "No guilds found for guild identifier `{identifier}`"

  public_interface_user_profile_description = "Show Deep Town user profile"

  public_interface_user_event_participations_description = "User event participations"

  public_interface_event_help_description = "Show items for current item"
  public_interface_event_help_item_scaling_levels_param_description = "Number of levels for which generate table of required items"
  public_interface_event_help_no_items = "Items not set for this event"
  public_interface_event_help_no_item_amount_scaling = "Material scaling not available"

  public_interface_event_current_description = "Show current event identifier and duration"

  public_interface_event_history_description = "Show history of event items"
  public_interface_event_history_no_events = "No events in database"

  public_interface_event_stats_description = "Show statistics about ocurences of items in events"
  public_interface_event_stats_year_param_description = "Specific year, without it show statistics for whole lifespan"
  public_interface_event_stats_no_stats = "No statistics available"

  public_interface_event_leaderboard_users_description = "Show leaderboard of participants in specific event"

  public_interface_event_leaderboard_guilds_description = "Show leaderboard of guilds in specific event"

  public_interface_event_leaderboard_limit_param_description = "Number results to display"

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
  blacklist_msg_com_add_invalid_target = "Invalid target message"

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

  # Questions and answers
  questions_and_answers_id_param_description = "Question and Answer ID"
  questions_and_answers_not_found = "Question and answer not in database"

  questions_and_answers_repond_format = "Maybe this is what you are looking for\n**Question:** {question}\n**Answer:** {answer}"

  questions_and_answers_add_description = "Add new question and answer"
  questions_and_answers_add_added = "New Q&A datapoint created"
  questions_and_answers_add_failed = "Failed to create new Q&A datapoint, maybe it already exists"

  questions_and_answers_modify_description = "Modify existing question and answer"

  questions_and_answers_remove_description = "Remove question and answer from database"
  questions_and_answers_remove_removed = "Question removed from database"

  questions_and_answers_list_description = "List all questions and answers"
  questions_and_answers_list_no_results = "No questions and answers available"

  questions_and_answers_whitelist_add_description = "Add guild channel to whitelist for automatic help"
  questions_and_answers_whitelist_add_success = "Channel `{channel}` added to whitelist for automatic help"
  questions_and_answers_whitelist_add_failed = "Channel `{channel}` is already on whitelist"

  questions_and_answers_whitelist_list_description = "List whitelisted channels for automatic help"
  questions_and_answers_whitelist_list_no_channels = "No whitelisted channels"

  questions_and_answers_whitelist_remove_description = "Remove guild channel from whitelist for automatic help"
  questions_and_answers_whitelist_remove_success = "Channel `{channel}` removed from whitelist for automatic help"
  questions_and_answers_whitelist_remove_failed = "Channel `{channel}` is not on whitelist"

  # Settings
  settings_admin_role_set_description = "Set discord guild admin role"
  settings_admin_role_set_admin_role_param_description = "Admin role to set"
  settings_admin_role_set_success = "Admin role {admin_role} set"
  settings_admin_role_set_failed = "Invalid admin role set"

  settings_admin_role_remove_description = "Remove discord guild admin role"
  settings_admin_role_remove_success = "Removed admin role"
  settings_admin_role_remove_failed = "Admin role is not set for this guild"

  settings_better_message_links_enable_description = "Enable better message link for this guild"
  settings_better_message_links_enable_success = "Better message links enabled"

  settings_better_message_links_disable_description = "Disable better message link for this guild"
  settings_better_message_links_disabled_success = "Better message links disabled"

  # Event Item Lottery
  lottery_invalid_item = "`{item_name}` is not valid item"

  lottery_button_listener_invalid_lottery = "Lotery doesn't exist, removing invalid message"
  lottery_button_listener_removed = "Lotery removed"
  lottery_button_listener_not_author = "You are not author of this lottery"
  lottery_already_created = "You already have lottery for next week created!"
  lottery_button_listener_invalid_command = "Invalid lottery message command received"
  lottery_failed_to_get_author = "Failed to create lottery, failed to get author"

  lottery_create_description = "Create event items lotery for next event"
  lottery_create_split_rewards_param_description = "Split reward amounts between winners"
  lottery_create_reward_item_param_description = "Reward item for guessing {item_number} event items right"
  lottery_create_reward_item_amount_param_description = "Number of reward items for guessing {item_number} event items right"
  lottery_create_no_reward_set = "You set no reward items"

  lottery_list_description = "List all lotteries on server"
  lottery_list_no_lotteries = "No lotteries in guild"

  lottery_guess_create_description = "Make a guess for next event items"
  lottery_guess_remove_description = "Remove guess for next event items"
  lottery_guess_for_create_description = "Make a guess for next event items for someone else"
  lottery_guess_for_remove_description = "Remove someone elses guess for next event items"
  lottery_guess_item_param_description = "Item guess {item_number}"
  lottery_guess_no_items = "You provided no items"
  lottery_guess_item_duplicates = "Detected item duplicates"
  lottery_guess_registered = "Guess registered for event `{event_year} {event_week}`\n`{items}`"

  lottery_guess_removed_sucessfully = "Guess removed"
  lottery_guess_no_guess_to_remove = "No guess to remove"
  lottery_guess_for_author_param_description = "User you managing guess for"

  lottery_auto_guess_whitelist_add_description = "Add guild channel to whitelist for automatic lottery guesses"
  lottery_auto_guess_whitelist_add_success = "Channel `{channel}` added to whitelist for automatic lottery guesses"
  lottery_auto_guess_whitelist_add_failed = "Channel `{channel}` is already on whitelist"

  lottery_auto_guess_whitelist_list_description = "List whitelisted channels for automatic lottery guesses"
  lottery_auto_guess_whitelist_list_no_channels = "No whitelisted channels"

  lottery_auto_guess_whitelist_remove_description = "Remove guild channel from whitelist for automatic lottery guesses"
  lottery_auto_guess_whitelist_remove_success = "Channel `{channel}` removed from whitelist for automatic lottery guesses"
  lottery_auto_guess_whitelist_remove_failed = "Channel `{channel}` is not on whitelist"

  lottery_update_description = "Update all lotteries, closed the ended ones and send results"
  lottery_update_no_active_lotteries = "No active lotteries to update"
  lottery_update_success = "Processed `{results}` lotteries and cleared `{guesses_cleared}` guesses"
