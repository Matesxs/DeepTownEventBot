from sqlalchemy import select

from database import run_query_in_thread
from database.tables.event_participation import EventParticipation, EventSpecification

async def have_participation_elsewhere(session, user_id: int, guild_id: int, event_year: int, event_week: int, amount: int) -> bool:
  result = await run_query_in_thread(session, select(EventParticipation)
                           .join(EventSpecification)
                           .filter(EventParticipation.dt_user_id == user_id,
                                   EventParticipation.dt_guild_id != guild_id,
                                   EventSpecification.event_year == event_year,
                                   EventSpecification.event_week == event_week,
                                   EventParticipation.amount >= amount)
                           .limit(1))
  return result.first() is not None
