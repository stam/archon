from .models import Base
from .controller import Controller
from .exceptions import UnauthorizedError, NoTargetError, InvalidTargetError, InvalidTypeError


class Router:
    def __init__(self):
        # Register models
        self.tree = {}
        self.register_base_routes(Controller)
        self.register_model(Base)

    def register_model(self, superclass):
        for M in superclass.__subclasses__():
            self.register_routes_for_model(M.__name__, M)
            self.register_model(M)

    def register_routes_for_model(self, target, M):
        self.tree[target] = {}
        c = getattr(M, 'controller', Controller)
        routes = []
        for m_name in dir(c):
            method = getattr(c, m_name)

            if getattr(method, 'is_route', False):
                routes.append(m_name)

        self.tree[target]['routes'] = routes
        self.tree[target]['Controller'] = c
        self.tree[target]['Model'] = M

    def register_base_routes(self, c):
        self.base_routes = []

        for m_name in dir(c):
            method = getattr(c, m_name)

            if getattr(method, 'is_targetless', False):
                self.base_routes.append(m_name)

    def route(self, db, connection, body):
        # Handle base route (no target needed)
        if body['type'] in self.base_routes:
            c = Controller(db, connection, body)
            method = getattr(c, body['type'])
            self.check_auth(c, method)
            return method()

        if 'target' not in body:
            raise NoTargetError()

        t_name = body['target'].title().replace('_', '')
        if t_name not in self.tree.keys():
            raise InvalidTargetError()

        target = self.tree[t_name]['Model']
        C = self.tree[t_name]['Controller']
        c = C(db, connection, body)
        method = getattr(c, body['type'], None)

        if not method or not getattr(method, 'is_route', False):
            raise InvalidTypeError()

        self.check_auth(c, method)
        # Call the method with the class as param
        return method(target)

    def check_auth(self, controller, method):
        public = getattr(method, 'is_public', False)
        auth_needed = not public
        if auth_needed:
            authorized = controller.check_auth()
            if not authorized:
                raise UnauthorizedError()
