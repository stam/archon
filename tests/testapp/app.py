from archon.app import create_app
from flask import jsonify
from .models import *  # noqa

app, db = create_app()


@app.route('/api/foo/', methods=['GET'])
def foo():
    return jsonify({'foo': 'bar'})
