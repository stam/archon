from chimera.models import db, Base


class Company(Base):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))
