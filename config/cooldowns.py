# Predefined cooldowns

from disnake.ext import commands

# 5x/30s
def short_cooldown(f):
    return commands.cooldown(rate=5, per=30.0, type=commands.BucketType.user)(f)

# 3x/30s
def default_cooldown(f):
    return commands.cooldown(rate=3, per=30.0, type=commands.BucketType.user)(f)

# 2x/60s
def long_cooldown(f):
    return commands.cooldown(rate=2, per=60.0, type=commands.BucketType.user)(f)

# 1x/5min
def huge_cooldown(f):
    return commands.cooldown(rate=1, per=300.0, type=commands.BucketType.user)(f)

# 2x/5min
def huge_cooldown_guild(f):
    return commands.cooldown(rate=2, per=300.0, type=commands.BucketType.guild)(f)
