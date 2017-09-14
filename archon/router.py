from .models import Base
from .controller import Controller
from .exceptions import UnauthorizedError, NoTargetError, InvalidTargetError, InvalidTypeError


class Router:
    def __init__(self):
        # Register models
        self.available_models = {}
        self.register_base_methods(Controller)
        self.register_model(Base)

    def register_model(self, superclass):
        for M in superclass.__subclasses__():
            self.available_models[M.__name__] = M
            self.register_model(M)

    def register_base_methods(self, c):
        self.base_methods = []
        for m_name in dir(c):
            method = getattr(c, m_name)

            if getattr(method, 'is_targetless', False):
                # from pudb import set_trace; set_trace()
                self.base_methods.append(m_name)

    def route(self, db, connection, body):
        c = Controller(db, connection, body)

        if body['type'] not in self.public_methods:
            authorized = c.check_auth()
            if not authorized:
                raise UnauthorizedError()

        if body['type'] in self.base_methods:
            method = getattr(c, body['type'])
            return method()

        if 'target' not in body:
            raise NoTargetError()

        t = body['target'].title().replace('_', '')
        if t not in self.available_models.keys():
            raise InvalidTargetError()

        target = self.available_models[t]
        method = getattr(c, body['type'], None)

        if not method or body['type'] not in ['save', 'update', 'delete', 'subscribe', 'unsubscribe', 'get']:
            raise InvalidTypeError()

        # Call the method with the class as param
        return method(target)

    @property
    def public_methods(self):
        return ['authenticate']
