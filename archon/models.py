from dateutil import parser, tz
from sqlalchemy.types import DateTime, Date, Enum
from flask_sqlalchemy import SQLAlchemy, _BoundDeclarativeMeta
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


class ArchonMeta(_BoundDeclarativeMeta):
    def __init__(self, name, bases, d):
        _BoundDeclarativeMeta.__init__(self, name, bases, d)
        self.__construct_core()

    # SQLAlchemy columns are a pain to traverse, you can't tell if
    # employee.customer is a foreign key without checking
    # len(employee.__table__.columns.company_id.foreign_keys).
    # So we do some indexing here
    def __construct_core(self):
        table = getattr(self, '__table__', None)
        if table is None:
            return

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

        self.__core__ = cols


class Base(db.Model, metaclass=ArchonMeta):
    __abstract__ = True

    def __init__(self, *args, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    def __repr__(self):
        return '<Model %r>' % self.id

    def parse(self, data, currentUser=None, reqType=None):
        for key, val in data.items():
            col = self.__core__[key]

            if isinstance(col, ForeignKey):
                setattr(self, key + '_id', data[key])
                continue

            if isinstance(col, DateTime) and val is not None:
                d = parser.parse(val)                                   # Convert to python datetime
                val = d.astimezone(tz.gettz('UTC')) if d.tzinfo else d  # Convert to UTC

            if isinstance(col, Date) and val is not None:
                val = parser.parse(val).date()

            setattr(self, key, val)

    def dump(self):
        data = {}
        for col_name, col in self.__core__.items():
            val = getattr(self, col_name)

            if isinstance(col, ForeignKey) and val is not None:
                val = getattr(self, col_name + '_id')

            if isinstance(col, DateTime) and val is not None:
                # Make aware and format as iso
                val = val.replace(tzinfo=tz.gettz('UTC')).isoformat()

            if isinstance(col, Date) and val is not None:
                val = val.isoformat()

            if isinstance(col, Enum) and val is not None:
                val = val.value

            data[col_name] = val
        return data

    @classmethod
    def find(cls, session, scope):
        query = session.query(cls)

        for key, val in scope.items():
            col = cls.__core__[key]

            # We want to filter by `company_id` if `company`
            # is given in the scope
            if isinstance(col, ForeignKey):
                key = key + '_id'

            query = query.filter_by(**{key: val})

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
