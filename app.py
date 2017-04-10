import os
import psycopg2
import urlparse
from user import User
from flask import *
from flask_login import LoginManager, UserMixin, login_required

# environment vars
SECRET_KEY = os.environ.get('SECRET_KEY')
DATABASE_URL = os.environ.get('DATABASE_URL')

# set up our app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY 
login_manager = LoginManager()
login_manager.init_app(app)


# open the database connection
def open_db_conn():
  urlparse.uses_netloc.append("postgres")
  url = urlparse.urlparse(DATABASE_URL)
  conn = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port)
  return conn

@app.route('/create/', methods=['POST'])
def create():
  error = None
  data = request.json
  user = data['username']
  pwd = data['password']
  
  if not user:
    error = 'Username required.'
  if not pwd:
    error = 'Password required.'

  conn = open_db_conn()
  cur = conn.cursor()
  stmt = 'INSERT INTO "User" ("Username", "Password") VALUES (\'{}\', \'{}\');'.format(user, pwd)
  cur.execute(stmt)

  response = 'Account created!'
  status = 200

  if error:
    response = error
    status = 406
  else:
    conn.commit()
  conn.close()
  return Response(response=response, status=status)

# @app.route('/edit/', methods=['POST'])
# def edit():
#   error = None
#   data = request.json
#   # user = data['username']
#   # pwd = data['password']
#   item = data['item']
#   new_value = data['new_value']

#   if item == 'Username':
#     item = 'Username'
#   elif item == 'Password':
#     item = 'Password'
#   elif item == 'TV_Username':
#     item = 'TV_Username'
#   elif item == 'OP_APIKey':
#     item = 'OP_APIKey'
  
#   conn = open_db_conn()
#   cur = conn.cursor()
#   stmt = 'INSERT INTO "User" ("Username", "Password") VALUES (\'{}\', \'{}\');'.format(user, pwd)
#   cur.execute(stmt)

#   response = 'Account created!'
#   status = 200

#   if error:
#     response = error
#     status = 406
#   else:
#     conn.commit()
#   conn.close()
#   return Response(response=response, status=status)

########################################################
#
# This stuff is for reference
#
########################################################

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

@app.route('/login/', methods=['POST'])
def login():
  return 

@app.route('/protected/', methods=['GET'])
@login_required
def protected():
  return Response(response='Hello Protected World!', status=200)


if __name__ == '__main__':
  app.run(port=5000, debug=True)