from dateutil import parser, tz
from sqlalchemy.types import DateTime, Date, Enum
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import orm
import datetime
import jwt
import os

db = SQLAlchemy()


class Collection():
    def __init__(self, models=[]):
        self.models = models

    def __len__(self):
        return len(self.models)

    def dump(self):
        return [m.dump() for m in self.models]


class ForeignKey(db.Integer):
    pass


class PrimaryKey(db.Integer):
    pass


class Base:
    def __init__(self, *args, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

        self.__construct_meta()

    # TODO: fix this with a metaclass?
    # SQLAlchemy does not call __init__
    @orm.reconstructor
    def init_on_load(self):
        self.__construct_meta()

    def __repr__(self):
        return '<Model %r>' % self.id

    # SQLAlchemy columns are a pain to traverse, you can't tell if
    # a employee.customer is a foreign key, without checking
    # len(employee.__table__.columns.company_id.foreign_keys)
    # so we do some indexing here
    def __construct_meta(self):
        cols = {}
        for col in self.__table__.columns:
            if col.primary_key is True:
                cols[col.name] = PrimaryKey()
                continue
            if len(col.foreign_keys) > 0:
                col_name_without_id = '_'.join(col.name.split('_')[:-1])
                cols[col_name_without_id] = ForeignKey()
                continue
            cols[col.name] = col.type

        self.__meta__ = cols

    def parse(self, data, currentUser=None, reqType=None):
        for key, val in data.items():
            if key not in self.__meta__:
                continue

            col = self.__meta__[key]

            if isinstance(col, ForeignKey):
                setattr(self, key + '_id', data[key])
                continue

            if isinstance(col, DateTime) and val is not None:
                d = parser.parse(val)                                   # Convert to python datetime
                val = d.astimezone(tz.gettz('UTC')) if d.tzinfo else d  # Convert to UTC

            if isinstance(col, Date) and val is not None:
                val = parser.parse(val).date()

            setattr(self, key, val)

    # TODO use __meta__
    def dump(self):
        data = {}
        for col in self.__table__.columns:
            key = col.name
            val = getattr(self, key)

            # Return {'project': id} instead of {'project_id': id}
            if len(col.foreign_keys):
                assert key.endswith('_id')
                key = '_'.join(key.split('_')[:-1])

            if type(col.type) == DateTime and val is not None:
                # Make aware and format as iso
                val = val.replace(tzinfo=tz.gettz('UTC')).isoformat()

            if type(col.type) == Date and val is not None:
                val = val.isoformat()

            if type(col.type) == Enum and val is not None:
                val = val.value

            data[key] = val
        return data

    # TODO use __meta__
    @classmethod
    def find(cls, session, scope):
        query = session.query(cls)

        for col in cls.__table__.columns:
            dbKey = col.name
            scopeKey = dbKey

            # Translate 'project_id' to 'project', a relation key shorthand
            if len(col.foreign_keys):
                assert dbKey.endswith('_id')
                scopeKey = '_'.join(dbKey.split('_')[:-1])

            if dbKey in scope or scopeKey in scope:
                val = scope[scopeKey]
                query = query.filter_by(**{dbKey: val})
                continue

        return Collection(query.all())


class User(Base, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100))
    username = db.Column(db.String(50))
    display_name = db.Column(db.String(50))
    avatar_url = db.Column(db.String(300))

    def create_session(self):
        secret = os.environ.get('CY_SECRET_KEY', '')
        payload = self.dump()
        payload['exp'] = datetime.datetime.utcnow() + datetime.timedelta(weeks=8)
        return jwt.encode(payload, secret, algorithm='HS256').decode('utf-8')
