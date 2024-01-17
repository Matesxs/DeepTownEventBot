alter table public.dt_active_entities_statistics
    rename to dt_active_entities_statistics_old;

create table public.dt_active_entities_statistics
(
    date          date    not null,
    active_guilds integer not null,
    active_users  integer not null,
    all_guilds    integer not null,
    all_users     integer not null
);

alter table public.dt_active_entities_statistics
    owner to deeptownbot;

alter table public.dt_active_entities_statistics
    add constraint dt_active_entities_statistics_pk
        primary key (date);

INSERT INTO dt_active_entities_statistics (date, active_guilds, active_users, all_guilds, all_users)
SELECT CAST(date as DATE) as date, active_guilds, active_users, all_guilds, all_users
FROM dt_active_entities_statistics_old
WHERE date IN (SELECT MAX(date)
               FROM dt_active_entities_statistics_old
               GROUP BY CAST(date as DATE))
ORDER BY date DESC;
COMMIT;

drop table public.dt_active_entities_statistics_old cascade;
