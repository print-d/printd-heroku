import os
import datetime
import json
import psycopg2
import requests
import urlparse
import uuid
from user import User
from flask import *
from flask_login import LoginManager, login_required
from werkzeug import generate_password_hash, check_password_hash

# environment vars
SECRET_KEY = os.environ.get('SECRET_KEY')
DATABASE_URL = os.environ.get('DATABASE_URL')
THINGIVERSE_CLIENT_ID = os.environ.get('THINGIVERSE_CLIENT_ID')
THINGIVERSE_CLIENT_SECRET = os.environ.get('THINGIVERSE_CLIENT_SECRET')

# set up our app
app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY
login_manager = LoginManager()
login_manager.init_app(app)

# parameters for upload
ALLOWED_EXTENSIONS = set(['ini', 'json'])


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

@app.route('/authenticatethingiverse/', methods=['POST'])
def auth_tv():
    token = request.headers.get('Authorization')
    user = authorize_user(token)
    data = request.json
    code = data['code']
    print(code)
    print(THINGIVERSE_CLIENT_ID)
    print(THINGIVERSE_CLIENT_SECRET)

    # POST https://www.thingiverse.com/login/oauth/access_token 
    res = requests.post('https://www.thingiverse.com/login/oauth/access_token?client_id={}&client_secret={}&code={}'.format(THINGIVERSE_CLIENT_ID, THINGIVERSE_CLIENT_SECRET, code))
    res = res.text
    print(res)
    access_token = res.split('&')[0]
    access_token = res.split('=')[1]
    # print(tv_token)

    # POST https://www.thingiverse.com/login/oauth/tokeninfo
    # res = resquests.post('https://www.thingiverse.com/login/oauth/tokeninfo?access_token={}'.format(access_token))
    return Response(response=access_token, status=200)

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
    print('Printer ID: {}'.format(printer_id))

    query = 'SELECT "ID" FROM "PrinterConfig" WHERE "PrinterID" = {};'.format(printer_id)
    cur.execute(query)
    config_id = cur.fetchone()[0]
    print('Config File ID: {}'.format(config_id))

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


@app.route('/login/', methods=['POST'])
def login():
    error = None
    status = 200
    response = None
    data = request.json

    user = data['username']
    pwd = data['password']

    conn = open_db_conn()
    cur = conn.cursor()

    query = 'SELECT "Password" FROM "User" WHERE "Username" = \'{}\';'.format(user)
    cur.execute(query)

    # check username
    pwd_hash = cur.fetchone()
    if pwd_hash != None:
        pwd_hash = pwd_hash[0]
    else:
        return Response(response='Invalid username.', status=406)

    # check password
    if check_password_hash(pwd_hash, pwd):
        response = 'Successfully logged in!'
    else:
        response = 'Invalid password.'
        status = 406

    # generate new session token & replace
    token = uuid.uuid4()
    response = str(token)
    stmt = 'UPDATE "Session" SET "Token" = \'{}\', "DateCreated" = \'{}\' WHERE "Username" = \'{}\';'.format(token, datetime.datetime.now(), user)
    try:
        cur.execute(stmt)
        conn.commit()
    except Exception:
        response = 'Error: login failed.'

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

        query = 'SELECT * FROM "Printer" WHERE "ID" = {};'.format(data[5])
        cur.execute(query)
        printer = cur.fetchone()
        print(printer)

        make = printer[4]
        model = printer[5]
        conn.close()

        data = {'id': data[0], 
            'username': data[1], 
            'op_apikey': data[3], 
            'printerconfigid': data[4], 
            'printerid': data[5],
            'make': make,
            'model': model
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
        print(data)

        if not data:
            return Response(response='Error! No data received.', status=406)

        new_user = data.get('username', None)
        if data.get('password'):
            new_pwd = generate_password_hash(data.get('password'))
        new_op_api = data.get('op_apikey', None)
        new_printer_config = data.get('printerconfigid', None)
        new_printer_make = data.get('make', None)
        new_printer_model = data.get('model', None)

        conn = open_db_conn()
        cur = conn.cursor()

        user = authorize_user(token)
        updated = []
        print(user)
        print(data)

        if new_user:
            return Response(response='Error! Username cannot be changed.', status=406)

        # update password
        if new_pwd:
            stmt = 'UPDATE "User" SET "Password" = \'{}\' WHERE "Username" = \'{}\';'.format(generate_password_hash(new_pwd), user)
            cur.execute(stmt)
            updated.append('password')

        # update api key
        if new_op_api:
            stmt = 'UPDATE "User" SET "OP_APIKey" = \'{}\' WHERE "Username" = \'{}\';'.format(new_op_api, user)
            cur.execute(stmt)
            updated.append('Octoprint API key')

        # update printer config file id
        if new_printer_config:
            stmt = 'UPDATE "User" SET "PrinterConfigID" = {} WHERE "Username" = \'{}\';'.format(new_printer_config, user)
            cur.execute(stmt)
            updated.append('printer config id')

        # update make/model
        if new_printer_make and new_printer_model:
            query = 'SELECT "ID" FROM "Printer" WHERE "Make" = \'{}\' AND "Model" = \'{}\';'.format(new_printer_make, new_printer_model)
            cur.execute(query)
            printer_id = cur.fetchone()[0]
            print('Printer ID: {}'.format(printer_id))
            stmt = 'UPDATE "User" SET "PrinterID" = \'{}\' WHERE "Username" = \'{}\';'.format(printer_id, user)
            cur.execute(stmt)
            updated.append('printer make & model')
        
        conn.commit()
        conn.close()
        updated = ', '.join(str(x) for x in updated)
        response = 'Successfully updated {}.'.format(updated)

        return Response(response=response, status=200)
    else:
        error = 'Invalid request'
        status = 406
        return Response(response=error, status=status)

# upload printer config files
@app.route('/upload/', methods=['POST'])
def upload():
    error = None
    file = request.files['config_file']
    filename = file.filename
    data = None
    status = 200

    # check to see if the file is OK
    if file and allowed_file(filename):
        try:
            print 'file is acceptable'
            data = file.read()
        except Exception:
            error = 'Error: Could not read file.'
            status = 400
    else:
        error = 'Error: invalid filetype.'
        status = 406
        # return Response(response='Error: invalid file type.', status=406)

    # if we didn't run into any problems, upload to db
    if not error:
        conn = open_db_conn()
        cur = conn.cursor()
        stmt = 'INSERT INTO "PrinterConfig" ("ConfigData", "Filename") VALUES ({}, \'{}\');'.format(psycopg2.Binary(data), filename)
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

# returns config file multipart of config file associated w/ your printer 
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

    return Response(response=config_file, status=200)

# returns list of config files associated with your printer
@app.route('/configfilelist/', methods=['GET'])
def get_config_file_list():
    token = request.headers.get('Authorization')
    user = authorize_user(token)

    conn = open_db_conn()
    cur = conn.cursor()

    query = 'SELECT "PrinterID" FROM "User" WHERE "Username" = \'{}\';'.format(user) 
    cur.execute(query)
    printer_id = cur.fetchone()[0]
    print(printer_id)

    query = 'SELECT * FROM "PrinterConfig" WHERE "PrinterID" = {};'.format(printer_id)
    cur.execute(query)

    files = []
    for row in cur:
        print(row)
        file = {'id': row[0],
                'printerid': row[2],
                'filename': row[3]
        }
        files.append(file) 

    print(files)
    conn.close()
    response = json.dumps(files)

    return Response(response=response, status=200)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)