from archon.models import db, Base


class Company(Base, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
