import os
from user import User
from flask import *
from flask_login import LoginManager, UserMixin, login_required

SECRET_KEY = os.environ.get('SECRET_KEY')

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.request_loader
def load_user(request):
  token = request.headers.get('Authorization')

  if token is None:
    token = request.args.get('token')
    
  if token is not None:
    username, password = token.split(":") #TODO: serialize this 
    user_entry = User.get(username)
    if user_entry is not None:
      user = User(user_entry[0], user_entry[1])
      if user.password == password:
        return user

    return None

@app.route('/', methods=['GET'])
def index():
  return Response(response='HELLO WORLD!', status=200)

@app.route('/protected/', methods=['GET'])
@login_required
def protected():
  return Response(response='Hello Protected World!', status=200)


if __name__ == '__main__':
  app.config['SECRET_KEY'] = SECRET_KEY 
  app.run(port=5000, debug=True)