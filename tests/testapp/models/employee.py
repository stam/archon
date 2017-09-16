from archon.models import db, Base


class Employee(Base, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200))

    company_id = db.Column(db.Integer, db.ForeignKey('company.id'))
    company = db.relationship('Company', backref=db.backref('employees', lazy='dynamic'))

    started_at = db.Column(db.DateTime)
    birthday = db.Column(db.Date)
