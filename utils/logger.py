# Custom logger for some beutiful consol logs

import logging
import coloredlogs
from config import config

logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

formatter_string = "%(asctime)s %(name)s {%(filename)s:%(lineno)d} %(levelname)s %(message)s"

if config.base.log_to_file:
	fh = logging.FileHandler("discord.log")
	fh.setLevel(logging.WARNING)
	fh.setFormatter(logging.Formatter(fmt=formatter_string, datefmt='%d-%m-%Y %H:%M:%S'))

def setup_custom_logger(name, override_log_level=None):
	logger = logging.getLogger(name)
	if config.base.log_to_file:
		logger.addHandler(fh)

	if not override_log_level:
		coloredlogs.install(fmt=formatter_string, level="INFO", logger=logger)
	else:
		coloredlogs.install(fmt=formatter_string, level=override_log_level, logger=logger)

	return logger