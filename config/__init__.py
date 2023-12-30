import sys

from features import dictionary_store
from . import cooldowns
from .strings import Strings

if len(sys.argv) > 1:
  config = dictionary_store.DictionaryStore.from_toml(sys.argv[1], "config/config.toml", "config/config.template.toml")
else:
  config = dictionary_store.DictionaryStore.from_toml("config/config.toml", "config/config.template.toml")
