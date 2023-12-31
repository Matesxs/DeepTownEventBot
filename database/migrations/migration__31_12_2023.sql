drop index public.ix_dt_guild_members_current_member;

alter table public.dt_guild_members
    drop column current_member;