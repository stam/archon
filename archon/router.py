import re
from flask import request
from .models import Base
from .controller import Controller
from .exceptions import UnauthorizedError, NoTargetError, InvalidTargetError, InvalidTypeError


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
                self.add_http_route(url, c, method, M)

        self.tree[target]['routes'] = routes
        self.tree[target]['Controller'] = c
        self.tree[target]['Model'] = M

    def add_http_route(self, url, Controller, route, Model):
        def wrapped_route():
            c = Controller(self.db, None, None, None)
            c.request = request
            method = getattr(c, route.__name__)
            return method(Model, request)

        options = getattr(route, 'options')
        endpoint = options.pop('endpoint', None)
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

    def route(self, connection, body, auth):
        # Handle base route (no target needed)
        if body['type'] in self.base_routes:
            c = Controller(self.db, connection, body, auth)
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
        c = C(self.db, connection, body, auth)
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
