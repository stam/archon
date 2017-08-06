from settings import Settings
from flask import Flask
import logging
from flask_sockets import Sockets


def create_app(settings=None):
    app = Flask(__name__)

    if settings:
        app.config.from_object(Settings)
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite://'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    sockets = Sockets(app)

    from chimera.models import db
    db.init_app(app)

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
