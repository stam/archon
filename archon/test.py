from collections import deque
from .models import User
from unittest import mock, TestCase as Case
from geventwebsocket.exceptions import WebSocketError
from geventwebsocket.websocket import MSG_ALREADY_CLOSED
from .hub import Hub
from greenlet import greenlet
import requests
import json
import collections


user_henk = {
    'name': 'Henk de Vries',
    'email': 'henk@devries.nl',
    'picture': 'bla',
}


class TestCase(Case):
    def setUp(self):
        self.client.app.app_context().push()
        self.client.db.create_all()

    # Reset the Hub
    # Otherwise the hub still has the socket of the previous test
    def tearDown(self):
        if self.client:
            self.client.app.hub = Hub()

        self.client.db.drop_all()


class LoggedInTestCase(TestCase):
    def setUp(self):
        super().setUp()

        # create and save a user
        u = User(user_henk)
        self.client.db.session.add(u)
        self.client.db.session.commit()

        # create a jwt token for that user
        token = u.create_session()
        self.client.auth_token = token


class MockWebSocket:
    closed = False
    connection = None
    auth_token = None

    def __init__(self):
        self.pending_actions = deque()
        self.outgoing_messages = []

    def send(self, message):
        if self.closed:
            raise WebSocketError(MSG_ALREADY_CLOSED)

        self.outgoing_messages.append(message)

    def close(self):
        # TODO:
        # self.connection.unsubscribe_all()
        self.closed = True

    def mock_incoming_message(self, msg):
        self.pending_actions.append(self.receive_message(msg))

    def resume_tests(self):
        g_self = greenlet.getcurrent()

        # Switch to the main thread if we are using greenlets.
        # Otherwise just close to jump out of the ws.receive loop
        if g_self.parent:
            g_self.parent.switch()
        else:
            self.close()

    def receive_message(self, msg):
        return msg

    def receive(self):
        result = None
        # Concurrency loop
        # This stack can contain a greenlet switch (method)
        # Or a message receive (str)
        while not result:
            if not len(self.pending_actions):
                self.resume_tests()
                return
            next_action = self.pending_actions.popleft()

            if callable(next_action):
                next_action()
            else:
                result = next_action
                # Add the auth_token for mocking loggeded in users
                if self.auth_token:
                    result['authorization'] = self.auth_token

        if isinstance(result, collections.Mapping):
            return json.dumps(result)

        return result


class MockResponse:
    def __init__(self, json_data={}, status_code=200):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data


def mock_api(url, **kwargs):
    return MockResponse({}, 200)


class Client:
    auth_token = None

    def __init__(self, app, db):
        self.app = app
        self.db = db
        self.app.testing = True
        self.http_client = self.app.test_client()
        self._mock_outgoing_requests()

    def __del__(self):
        self._outgoing_requests.stop()

    def open_connection(self, ws, url='/api/', app=None):
        if app:
            # So for some reason, Flask loses its application context
            # when switching between greenlets?
            app.app_context().push()

        if self.auth_token:
            ws.auth_token = self.auth_token

        # We need to invoke a websocket route with the given url
        # No idea why we can't match on just the url_map
        # So we bind it to an empty context.
        context = self.app.wsgi_app.ws.url_map.bind('')

        # Don't really know what the second part in the matched result tuple is
        route = context.match(url)[0]

        route(ws)

    def set_mock_api(self, func):
        self._api_mock.side_effect = func

    def _mock_outgoing_requests(self):
        self._api_mock = mock.MagicMock(side_effect=mock_api)
        self._outgoing_requests = mock.patch.object(requests, 'post', self._api_mock)
        self._outgoing_requests.start()
