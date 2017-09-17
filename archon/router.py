import re
from flask import request, jsonify
from .models import Base
from .controller import Controller
from .exceptions import UnauthorizedError, NoTargetError, InvalidTargetError, InvalidTypeError
import jwt
import os
from .models import User


class Router:
    def __init__(self, app, db):
        # Register models
        self.app = app
        self.db = db
        self.tree = {}
        self.register_base_routes(Controller)
        self.register_model(Base)

    def register_model(self, superclass):
        for M in superclass.__subclasses__():
            self.register_routes_for_model(self.to_snake(M.__name__), M)
            self.register_model(M)

    def register_routes_for_model(self, target, M):
        self.tree[target] = {}
        c = getattr(M, 'Controller', Controller)
        routes = []
        for m_name in dir(c):
            method = getattr(c, m_name)

            if getattr(method, 'is_route', False):
                routes.append(m_name)

            if getattr(method, 'is_http_route', False):
                url = '/api/{}/{}/'.format(target, m_name)
                self.add_http_route(url, c, method, target)

        self.tree[target]['routes'] = routes
        self.tree[target]['Controller'] = c
        self.tree[target]['Model'] = M

    def add_http_route(self, url, C, route, target):
        def wrapped_route():
            return self.route_http(request, C, route, target)

        options = getattr(route, 'options')
        endpoint = options.pop('endpoint', route.__name__)
        self.app.add_url_rule(url, endpoint, wrapped_route, **options)

    def to_snake(self, name):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def register_base_routes(self, c):
        self.base_routes = []

        for m_name in dir(c):
            method = getattr(c, m_name)

            if getattr(method, 'is_targetless', False):
                self.base_routes.append(m_name)

    def route_http(self, req, C, route, target):
        body = {}
        body['authorization'] = req.args.get('authorization')
        auth = self.check_auth(body)
        body['target'] = target
        M = self.tree[target]['Model']
        body['type'] = route.__name__

        try:
            c = C(self.db, body, auth, request=request)
            method = getattr(c, route.__name__)

            self.require_auth(c, method, auth)
            res = method(M, request)
        except Exception as e:
            if isinstance(e, UnauthorizedError) or not auth:
                response = jsonify({'message': UnauthorizedError.message})
                response.status_code = 403
            # elif isinstance(e, ArchonError):
            #     response = jsonify({'message', e.message})
            #     response.status_code = 412
            else:
                response = jsonify({'message': str(e)})
                response.status_code = 500
            return response

        return jsonify(res)

    def check_auth(self, body):
        currentUser = None
        if 'authorization' not in body:
            return False

        try:
            userData = jwt.decode(body['authorization'], os.environ.get('CY_SECRET_KEY', ''), algorithms=['HS256'])
            currentUser = User.query.get(userData['id'])
        except jwt.InvalidTokenError:
            return False

        return currentUser

    def route(self, connection, body, auth):
        # Handle base route (no target needed)
        if body['type'] in self.base_routes:
            c = Controller(self.db, body, auth, connection=connection)
            method = getattr(c, body['type'])
            self.require_auth(c, method, auth)
            return method()

        if 'target' not in body:
            raise NoTargetError()

        t_name = body['target']
        if t_name not in self.tree.keys():
            raise InvalidTargetError()

        target = self.tree[t_name]['Model']
        C = self.tree[t_name]['Controller']
        c = C(self.db, body, auth, connection=connection)
        method = getattr(c, body['type'], None)

        if not method or not getattr(method, 'is_route', False):
            raise InvalidTypeError()

        self.require_auth(c, method, auth)
        # Call the method with the class as param
        return method(target)

    def require_auth(self, controller, method, auth):
        public = getattr(method, 'is_public', False)
        if not public and not auth:
            raise UnauthorizedError()
