import datetime

def get_event_index(date:datetime.datetime):
  event_year = date.year
  week_number = date.isocalendar()[1]

  if date.month == 1 and week_number > 5:
    event_year -= 1

  if date.weekday() < 3 or (date.weekday() == 3 and date.hour < 8):
    week_number -= 1

  if week_number <= 0:
    event_year -= 1
    week_number = datetime.date(event_year, 12, 28).isocalendar()[1]

  return event_year, week_number