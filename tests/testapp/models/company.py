from archon.models import db, Base
from archon.controller import Controller, model_route


class CompanyController(Controller):
    @model_route
    def ask_for_raise(self, cls):
        return {
            'answer': 'no',
            'code': 'error',
        }


class Company(Base, db.Model):
    Controller = CompanyController

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
