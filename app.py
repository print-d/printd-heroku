import os
import psycopg2
import urlparse
from passlib.hash import pbkdf2_sha256
from flask import *




urlparse.uses_netloc.append("postgres")
url = urlparse.urlparse(os.environ["DATABASE_URL"])

conn = psycopg2.connect(
    database=url.path[1:],
    user=url.username,
    password=url.password,
    host=url.hostname,
    port=url.port
)



app = Flask(__name__)

@app.route('/')
def home():
	hash = pbkdf2_sha256.hash("turtle1")
	print("!*!*!**!!*!*!*!*!**!*!*!*!*!**!*!*!*!*!*!*!*")
	print(pbkdf2_sha256.verify("turtle1", hash))
	print("!*!*!*!*!*!*!**!*!*!*!*!*!*!**!!**!*!*!*!*!")
	return hash

@app.route('/test', methods=['POST'])
def generate_user():
	return 'This is a test post'
	

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
