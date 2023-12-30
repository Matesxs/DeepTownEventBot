alter table public.tracking_settings
    rename column announce_channel_id to text_announce_channel_id;

alter table public.tracking_settings
    add csv_announce_channel_id varchar;

alter table public.dt_event_item_lotteries
    add autoping_winners boolean default false not null;

alter table public.discord_guilds
    alter column enable_better_message_links set default false;
