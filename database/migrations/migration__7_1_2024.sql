alter table public.discord_users
    add created_at timestamp;

alter table public.discord_members
    add joined_at timestamp;