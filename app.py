import os
#import psycopg2
import requests
import urlparse
import uuid
from flask import *

urlparse.uses_netloc.append("postgres")
URL = urlparse.urlparse(os.environ["DATABASE_URL"])





app = Flask(__name__)

@app.route('/')
def home():
    return 'Testing!'

#@app.route('/test', methods=['POST'])
#def generate_user():
	#return 'This is a test post'
	

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
