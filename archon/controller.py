import json
import os
import requests
import copy
import base64
from .models import User


def targetless_route(func):
    func.is_targetless = True
    func.is_route = True
    return func


def public_route(func):
    func.is_public = True
    return func


def model_route(func):
    func.is_route = True
    return func


def http_route(**options):
    def decorator(func):
        func.is_http_route = True
        func.options = options
        return func
    return decorator


class Controller:
    db = None
    connection = None
    body = None
    currentUser = None

    def __init__(self, db, body, currentUser, connection=None, request=None):
        self.db = db
        self.connection = connection
        self.request = request
        self.body = body
        self.currentUser = currentUser

    def error(self, msg):
        return {
            'type': self.body['type'],
            'code': 'error',
            'message': msg if msg else '',
        }

    @targetless_route
    def bootstrap(self):
        output = copy.copy(self.currentUser.dump())
        return {
            'type': self.body['type'],
            'code': 'success',
            'data': output,
        }

    @model_route
    def save(self, cls):
        data = self.body['data']

        # Create instance if id is not given
        # Ignore binary post data (file upload)
        if not type(data) == bytes and 'id' in data and data['id'] is not None:
            return self.error('ID given when saving, try using type=update')

        try:
            m = cls(data, self.currentUser)
        except Exception as e:
            return self.error(str(e))

        self.db.session.add(m)
        self.db.session.commit()

        result = m.dump()
        return {
            'type': self.body['type'],
            'target': self.body['target'],
            'code': 'success',
            'data': result,
        }

    @model_route
    def update(self, cls):
        data = self.body['data']

        # Create instance if id is not given
        if 'id' not in data or data['id'] is None:
            return self.error('No id given')

        m = self.db.session.query(cls).get(data['id'])
        mSnapshot = m.dump()
        m.parse(data, self.currentUser, 'update')

        self.db.session.add(m)
        self.db.session.commit()

        result = m.dump()
        return {
            'type': self.body['type'],
            'target': self.body['target'],
            'snapshot': mSnapshot,
            'code': 'success',
            'data': result,
        }

    @model_route
    def delete(self, cls):
        data = self.body.get('data')
        if not data:
            return self.error('No data given')

        # Create instance if id is not given
        if 'id' not in data or data['id'] is None:
            return self.error('No id given')

        m = self.db.session.query(cls).get(data['id'])
        self.db.session.delete(m)
        self.db.session.commit()

        result = m.dump()
        return {
            'type': self.body['type'],
            'target': self.body['target'],
            'code': 'success',
            'requestId': self.body.get('requestId', None),
            'data': result,
        }

    @model_route
    def subscribe(self, cls):
        scope = self.body['data'] if 'data' in self.body else {}

        result = cls.find(self.db.session, scope)

        # Mark the socket as subscribing so we know what is listening to what
        self.connection.subscribe(self.body['requestId'], self.body['target'], scope)

        if 'requestId' not in self.body:
            return self.error('No requestId given')

        return {
            'type': 'publish',
            'target': self.body['target'],
            'code': 'success',
            'requestId': self.body['requestId'],
            'data': {
                'add': result.dump(),
                'update': [],
                'delete': [],
            }
        }

    @targetless_route
    def unsubscribe(self):
        reqId = self.body.get('requestId', None)

        if not reqId:
            return self.error('No requestId given')

        success = self.connection.unsubscribe(reqId)
        if not success:
            return self.error('Invavlid requestId given')

        return {
            'type': 'unsubscribe',
            'code': 'success',
            'requestId': self.body['requestId'],
        }

    @public_route
    @targetless_route
    def authenticate(self):
        data = {
            'client_id': os.environ.get('CY_OAUTH_CLIENT_ID'),
            'client_secret': os.environ.get('CY_OAUTH_CLIENT_SECRET'),
            'redirect_uri': os.environ.get('CY_REDIRECT_URI'),
            'code': self.body['data']['code'],
            'grant_type': 'authorization_code',
        }

        r1 = requests.post(os.environ.get('CY_OAUTH_URL'), params=data)

        if r1.status_code != 200:
            return self.error(r1.json()['error_description'])

        # Alright so for some reason, google returns the client info encapsulated in a JWT token.
        # This JWT token has an invalid signature, so we just b64 decode the body.
        #
        # https://stackoverflow.com/questions/16923931/python-google-ouath-authentication-decode-and-verify-id-token
        token = r1.json()['id_token'].split('.')

        # Repad the b64 body
        body_encoded = token[1]
        body_repadded = body_encoded + '=' * (4 - len(body_encoded) % 4)
        body_decoded = base64.urlsafe_b64decode(body_repadded).decode()
        u_data = json.loads(body_decoded)

        user = self.db.session.query(User).filter(User.email == u_data['email']).first()

        if not user:
            u = {
                'username': u_data['name'],
                'email': u_data['email'],
                'avatar_url': u_data['picture'],
                'display_name': u_data['name'],
            }
            user = User(u)
            self.db.session.add(user)
            self.db.session.commit()

        token = user.create_session()

        return {
            'type': 'authenticate',
            'code': 'success',
            'authorization': token,
        }


# class SocketController(BaseController):
#     db = None
#     requestContainer = None
#     body = None
#     currentUser = None

#     def __init__(self, db, socketContainer, message):
#         super().__init__()
#         self.db = db
#         self.socketContainer = socketContainer
#         self.message = message

#     def handle(self):
#         if self.message == 'ping':
#             # todo keepalive logic
#             return 'pong'

#         self.body = self._parse_body()
#         return self.follow()

#     def _parse_body(self):
#         return json.loads(self.message)


# class RequestController(BaseController):
#     db = None
#     request = None
#     body = None
#     currentUser = None

#     def __init__(self, db, request):
#         super().__init__()
#         self.db = db
#         self.request = request

#     def handle(self):
#         self.body = self._parse_body()
#         return self.follow()

#     def _get_type(self, request):
#         if request.method == 'POST':
#             return 'save'
#         if request.method == 'PUT' or request.method == 'PATCH':
#             return 'update'
#         if request.method == 'DELETE':
#             return 'delete'
#         if request.method == 'GET':
#             return 'get'
#         return False

#     def _parse_body(self):
#         body = {}
#         req = self.request
#         body['authorization'] = req.args.get('authorization')
#         body['target'] = req.endpoint
#         body['type'] = self._get_type(req)
#         if body['type'] == 'save' and not req.data:
#             if not req.files:
#                 self.error('save without data or file detected')
#             body['data'] = {'file': req.files['file']}

#         return body
