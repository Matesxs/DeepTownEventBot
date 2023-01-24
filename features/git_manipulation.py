import git

class Git:
  def __init__(self):
    self.repo = git.Repo(search_parent_directories=True)

  async def pull(self):
    return self.repo.remote("master").pull()

  def short_hash(self):
    return self.repo.head.object.hexsha[:7]
