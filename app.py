
import os
import psycopg2
import urlparse
from flask import *

urlparse.uses_netloc.append("postgres")
URL = urlparse.urlparse(os.environ["DATABASE_URL"])

CONN = psycopg2.connect(
    database=URL.path[1:],
    user=URL.username,
    password=URL.password,
    host=URL.hostname,
    port=URL.port
)



app = Flask(__name__)

@app.route('/')
def home():
    return 'Testing!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
