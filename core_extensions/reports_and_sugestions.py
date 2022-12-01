from features.base_cog import Base_Cog

class ReportsAndSugestions(Base_Cog):
  def __init__(self, bot):
    super(ReportsAndSugestions, self).__init__(bot, __file__)

def setup(bot):
  bot.add_cog(ReportsAndSugestions(bot))
