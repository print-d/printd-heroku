import os
import datetime
import json
import psycopg2
import urlparse
import uuid
from user import User
from flask import *
from flask_login import LoginManager, login_required
from werkzeug import generate_password_hash, check_password_hash

# environment vars
SECRET_KEY = os.environ.get('SECRET_KEY')
DATABASE_URL = os.environ.get('DATABASE_URL')

# set up our app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
login_manager = LoginManager()
login_manager.init_app(app)

# parameters for upload
ALLOWED_EXTENSIONS = set(['ini'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    
    # required fields
    user = data['Username']
    pwd = generate_password_hash(data['Password'])
    op_api = data['OP_APIKey']
    printer_make = data['Make']
    printer_model = data['Model']
    token = uuid.uuid4()

    # check for blank entries
    if not user:
        error = 'Username required.'
    if not pwd:
        error = 'Password required.'
    
    # open the database connection
    conn = open_db_conn()
    cur = conn.cursor()

    # insert into user table
    stmt = 'INSERT INTO "User" ("Username", "Password") VALUES (\'{}\', \'{}\');'.format(user, pwd)
    cur.execute(stmt)
    response = str(token)
    status = 200

    # create session
    stmt = 'INSERT INTO "Session" ("Username", "Token", "DateCreated") VALUES(\'{}\', \'{}\', \'{}\');'.format(user, token, datetime.datetime.now())
    cur.execute(stmt)

    # check for any last errors
    if error:
        response = error
        status = 406
    else:
        conn.commit()
    conn.close()
    return Response(response=response, status=status)

# upload printer config files
@app.route('/upload/', methods=['POST'])
def upload():
    error = None
    file = request.files['config_file']
    data = None
    status = 200

    # check to see if the file is OK
    if file and allowed_file(file.filename):
        try:
            print 'file is acceptable'
            data = file.read()
        except Exception:
            error = 'Error: Could not read file.'
            status = 400

    # if we didn't run into any problems, upload to db
    if not error:
        conn = open_db_conn()
        cur = conn.cursor()
        stmt = 'INSERT INTO "PrinterConfig" ("ConfigData") VALUES ({});'.format(psycopg2.Binary(data))
        cur.execute(stmt)
        conn.commit()
        conn.close()
    response = 'Printer configuration file uploaded!'
    status = 200
    return Response(response=response, status=status)

@app.route('/printerdata/', methods=['GET'])
def printer_data():
    error = None
    status = 200
    
    conn = open_db_conn()
    cur = conn.cursor()
    stmt = 'SELECT * FROM "Printer";'
    cur.execute(stmt)

    printers = []
    for row in cur:
        printer = {'ID': row[0], 
            'Make': row[4], 
            'Model': row[5], 
            'x_size': row[1], 
            'y_size': row[2], 
            'z_size': row[3]}
        printers.append(printer)

    data = json.dumps({'title': 'Printer Data', 'printers': printers})
    response = app.response_class(
        response=data,
        status=200,
        mimetype='application/json'
    )
    
    return response

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
        username, password = token.split(":")  # TODO: serialize this
        user_entry = User.get(username)
        if user_entry is not None:
            user = User(user_entry[0], user_entry[1])
            if user.password == password:
                return user

    return None

@app.route('/login/', methods=['POST'])
def login():
    # check username
    # check password hash
    # generate new session token & replace
    return


@app.route('/protected/', methods=['GET'])
@login_required
def protected():
    return Response(response='Hello Protected World!', status=200)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    # app.run(port=5000, debug=True)
