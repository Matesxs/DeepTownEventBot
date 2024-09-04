BEGIN;
alter table public.dt_guilds
    add created_at timestamp default to_timestamp(0);

alter table public.dt_users
    add created_at timestamp default to_timestamp(0);

alter table public.dt_guild_members
    add created_at timestamp default to_timestamp(0);
END;
