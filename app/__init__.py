from flask import Flask, jsonify, request, abort, make_response
from flask_cors import CORS
from datetime import timedelta
from datetime import datetime
from flask_pymongo import PyMongo
from bson import ObjectId
from flask_jwt_extended import JWTManager, jwt_required,get_jwt_identity, unset_jwt_cookies, create_access_token
#quickfix 
from app.fix_application.settings_fix import config_fix_settings
#BroadcasterWebsocketServer
from app.WebSocket.BroadcasterWebsocketServer import BroadcasterWebsocketServer
import logging
import time
import asyncio
from app.clases.fixManager import fixManager


#server Broadcaster
server_md = BroadcasterWebsocketServer('0.0.0.0', 5100)
server_md.start()


logging.basicConfig(filename=f'reports.log', level=logging.INFO,
                    format='%(asctime)s %(name)s  %(levelname)s  %(message)s  %(lineno)d ')
log = logging.getLogger(__name__)
   
app = Flask(__name__)
cors = CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

app.config["JWT_SECRET_KEY"] = "xls**/54199021Nanaas4d8asd4/7/6238742347--.@"  # Change this!
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(hours=999999)
app.config['MONGO_URI'] = 'mongodb://localhost:27017/rofex'
jwt = JWTManager(app)
mongo = PyMongo(app)
sesionesFix = {}
thread = {}
fixM = fixManager()

from app.request import *

