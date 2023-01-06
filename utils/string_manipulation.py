import math
from typing import List, Tuple, Union

def add_string_until_length(strings:List[str], max_length:int, sep:str) -> Tuple[str, List[str]]:
  output = ""
  while strings:
    string = strings[0]
    tmp_output = (output + string) if output == "" else (output + sep + string)
    if len(tmp_output) > max_length:
      break

    strings.pop(0)
    output = tmp_output
  return output, strings

def truncate_string(string: str, limit: int, ellipsis :str="…", from_beginning: bool=False, strip: bool=True) -> str:
  if strip:
    string = string.strip()
  if len(string) <= limit: return string

  if from_beginning:
    return ellipsis + string[len(string) - limit + len(ellipsis):]
  else:
    return string[:limit - len(ellipsis)] + ellipsis

def split_to_parts(items: str, length: int) -> List[str]:
  result = []

  for x in range(math.ceil(len(items) / length)):
    result.append(items[x * length:(x * length) + length])

  return result

def format_number(number: Union[int, float], precision: int=2) -> str:
  if isinstance(number, int):
    number = float(number)

  units = ""
  if number / 1_000_000_000_000 >= 1:
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
