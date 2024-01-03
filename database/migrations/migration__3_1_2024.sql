alter table public.dt_event_item_lotteries
    add created_at timestamp default now() not null;

alter table public.dt_event_item_lottery_guesses
    add created_at timestamp default now() not null;