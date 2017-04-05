import os
import psycopg2
from urllib.parse import urlparse
from passlib.hash import pbkdf2_sha256
from flask import *

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
