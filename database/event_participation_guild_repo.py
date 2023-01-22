from sqlalchemy import func, select

from database import run_query
from database.tables.event_participation import EventParticipation, EventSpecification

async def get_guild_activity(guild_id: int, last_events: int, activity_threshold: float=0.0) -> bool:
  amounts_query = select(func.sum(EventParticipation.amount).label("event_sum"))\
                         .join(EventSpecification)\
                         .filter(EventParticipation.dt_guild_id == guild_id)\
                         .group_by(EventSpecification.event_year, EventSpecification.event_week)\
                         .order_by(EventSpecification.event_year.desc(), EventSpecification.event_week.desc())\
                         .limit(last_events)\
                         .subquery()
  result = await run_query(select(func.sum(amounts_query.c.event_sum) > activity_threshold))
  return result.scalar_one_or_none() is True