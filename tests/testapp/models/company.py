from archon.models import db, Base
from archon.controller import Controller, model_route, http_route
from flask import jsonify


class CompanyController(Controller):
    @model_route
    def ask_for_raise(self, cls):
        return {
            'answer': 'no',
            'code': 'error',
        }

    @http_route(methods=['GET'])
    def foo(self, cls, request):
        return jsonify({'foo': 'bar'})


class Company(Base, db.Model):
    Controller = CompanyController

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
