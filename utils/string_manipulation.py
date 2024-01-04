import math
from typing import List, Tuple, Union, Optional

def add_string_until_length(strings:List[str], max_length:int, sep:str, max_connections: Optional[int] = None) -> Tuple[str, List[str]]:
  output = ""
  connection_count = 0

  while strings:
    if len(strings[0]) > max_length:
      parts = split_to_parts(strings[0], max_length)
      strings.pop()
      strings = [*parts, *strings]
      continue

    tmp_output = (output + strings[0]) if output == "" else (output + sep + strings[0])
    if len(tmp_output) > max_length:
      break

    strings.pop(0)
    connection_count += 1
    output = tmp_output

    if max_connections is not None and connection_count >= max_connections:
      break
  return output, strings

def truncate_string(string: str, limit: int, ellipsis: str = "…", from_beginning: bool = False, strip: bool = True) -> str:
  if strip:
    string = string.strip()
  if len(string) <= limit: return string

  if from_beginning:
    return ellipsis + string[len(string) - limit + len(ellipsis):]
  else:
    return string[:limit - len(ellipsis)] + ellipsis

def split_to_parts(item: str, length: int) -> List[str]:
  result = []

  for x in range(math.ceil(len(item) / length)):
    result.append(item[x * length:(x * length) + length])

  return result

def format_number(number: Union[int, float], precision: int=2) -> str:
  if isinstance(number, int):
    number = float(number)

  units = ""
  if number / 1_000_000_000_000_000 >= 1:
    number /= 1_000_000_000_000_000
    units = "P"
  elif number / 1_000_000_000_000 >= 1:
    number /= 1_000_000_000_000
    units = "T"
  elif number / 1_000_000_000 >= 1:
    number /= 1_000_000_000
    units = "G"
  elif number / 1_000_000 >= 1:
    number /= 1_000_000
    units = "M"
  elif number / 1_000 >= 1:
    number /= 1_000
    units = "k"
  elif number >= 1:
    pass
  elif number * 1_000 >= 1:
    number *= 1_000
    units = "m"
  elif number * 1_000_000 >= 1:
    number *= 1_000_000
    units = "u"

  return f"{number:.{precision}f}{units}"
