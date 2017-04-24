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


def authorize_user(token):
    conn = open_db_conn()
    cur = conn.cursor()

    query = 'SELECT "Username" FROM "Session" WHERE "Token" = \'{}\';'.format(token)
    cur.execute(query)
    user = cur.fetchone()[0]

    conn.close()
    return user

@app.route('/create/', methods=['POST'])
def create():
    error = None
    data = request.json

    # required fields
    user = data['username']
    pwd = generate_password_hash(data['password'])
    op_api = data['op_apikey']
    printer_make = data['make']
    printer_model = data['model']
    token = uuid.uuid4()

    # check for blank entries
    if not user:
        error = 'Username required.'
    if not pwd:
        error = 'Password required.'
    
    # open the database connection
    conn = open_db_conn()
    cur = conn.cursor()

    query = 'SELECT "ID" FROM "Printer" WHERE "Make" = \'{}\' AND "Model" = \'{}\';'.format(printer_make, printer_model)
    cur.execute(query)
    printer_id = cur.fetchone()[0]

    query = 'SELECT "ID" FROM "PrinterConfig" WHERE "PrinterID" = {};'.format(printer_id)
    cur.execute(query)
    config_id = cur.fetchone()[0]

    # insert into user table
    stmt = '''INSERT INTO "User" ("Username", "Password", "OP_APIKey", "PrinterConfigID", "PrinterID") 
        VALUES (\'{}\', \'{}\', \'{}\', {}, {});'''.format(user, pwd, op_api, config_id, printer_id)
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

# edit user account data
@app.route('/userdata/', methods=['GET', 'POST'])
def user_data():
    error = None
    status = 200
    token = request.headers.get('Authorization')

    # return data on a user
    if request.method == 'GET':
        conn = open_db_conn()
        cur = conn.cursor()

        user = authorize_user(token)

        query = 'SELECT * FROM "User" WHERE "Username" = \'{}\';'.format(user)
        cur.execute(query)
        data = cur.fetchone()
        print(data)

        conn.close()

        data = {'id': data[0], 
            'username': data[1], 
            'op_apikey': data[3], 
            'printerconfigid': data[4], 
            'printerid': data[5] 
        }

        data = json.dumps(data)
        response = app.response_class(
            response=data,
            status=200,
            mimetype='application/json'
        )
        return response

    # if a user is editing their account
    elif request.method == 'POST':
        data = request.json
        user = data['username']
        pwd = generate_password_hash(data['password'])
        op_api = data['op_apikey']
        printer_make = data['make']
        printer_model = data['model']
        return Response(response='POST request', status=200)
    else:
        error = 'Invalid request'
        status = 406
        return Response(response=error, status=status)

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

# return all printer data, used during account creation to select a printer
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
        printer = {'id': row[0], 
            'make': row[4], 
            'model': row[5], 
            'x_size': row[1], 
            'y_size': row[2], 
            'z_size': row[3]}
        printers.append(printer)

    conn.close()

    data = json.dumps({'title': 'Printer Data', 'printers': printers})
    response = app.response_class(
        response=data,
        status=200,
        mimetype='application/json'
    )
    return response

@app.route('/dimensions/', methods=['GET'])
def get_dimensions():
    token = request.headers.get('Authorization')

    conn = open_db_conn()
    cur = conn.cursor()

    user = authorize_user(token)

    query = 'SELECT "PrinterID" FROM "User" WHERE "Username" = \'{}\';'.format(user)
    cur.execute(query)
    printer_id = cur.fetchone()[0]

    query = 'SELECT * FROM "Printer" WHERE "ID" = {};'.format(printer_id)
    cur.execute(query)
    printer = cur.fetchone()

    conn.close()

    printer = {
        'id': printer[0], 
        'make': printer[4], 
        'model': printer[5], 
        'x_size': printer[1], 
        'y_size': printer[2], 
        'z_size': printer[3]
    }

    data = json.dumps(printer)
    response = app.response_class(
        response=data,
        status=200,
        mimetype='application/json'
    )
    return response

@app.route('/configfile/', methods=['GET'])
def get_config_file():
    token = request.headers.get('Authorization')

    conn = open_db_conn()
    cur = conn.cursor()

    query = 'SELECT "Username" FROM "Session" WHERE "Token" = \'{}\';'.format(token)
    cur.execute(query)
    user = cur.fetchone()[0]

    query = 'SELECT "PrinterConfigID" FROM "User" WHERE "Username" = \'{}\';'.format(user)
    cur.execute(query)
    config_id = cur.fetchone()[0]
    print(config_id)

    query = 'SELECT "ConfigData" FROM "PrinterConfig" WHERE "ID" = {}'.format(config_id)
    cur.execute(query)
    config_file = cur.fetchone()[0]
    print(config_file)

    conn.close()

    response = app.response_class(
        response=config_file,
        status=200,
        mimetype='application/octet-stream'
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
