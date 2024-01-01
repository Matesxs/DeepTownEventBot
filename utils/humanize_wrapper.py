import humanize
import datetime

def hum_naturaltime(value: datetime.datetime | datetime.timedelta | float,
                    future: bool = False,
                    months: bool = True,
                    minimum_unit: str = "seconds",
                    when: datetime.datetime | None = None,
                    only_first: bool = False):
  result = humanize.naturaltime(value, future, months, minimum_unit, when)

  if only_first:
    splits = result.split(",")
    if len(splits) > 1:
      postfix = splits[-1].split(" ")[-1].strip()
      result = f"{splits[0].strip()} {postfix}"

  return result
