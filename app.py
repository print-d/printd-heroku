import os
from passlib.hash import pbkdf2_sha256
from flask import *

app = Flask(__name__)

@app.route('/')
def home():
	hash = pbkdf2_sha256.hash("testpassword")
	return hash

@app.route('/test', methods=['POST'])
def generate_user():
	return 'This is a test post'
	

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
