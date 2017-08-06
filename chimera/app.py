from settings import Settings
from flask import Flask
import logging
from flask_sockets import Sockets
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object(Settings)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
sockets = Sockets(app)
db = SQLAlchemy(app)

from chimera.hub import Hub
hub = Hub()


@sockets.route('/api/')
def open_socket(ws):
    socket = hub.add(ws)
    while not socket.ws.closed:
        message = socket.ws.receive()
        if message:
            try:
                socket.handle(db, message)
            except Exception as e:
                logging.error(e, exc_info=True)
