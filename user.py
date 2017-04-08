from flask_login import UserMixin

class User(UserMixin):

  #TODO: change to access an actual database instead of proxy
  user_database = {"JohnDoe": ("JohnDoe", "John"),
          "JaneDoe": ("JaneDoe", "Jane")}
  
  def __init__(self, username, password):
    self.id = username
    self.password = password

  @classmethod
  def get(cls, id):
    return cls.user_database.get(id)