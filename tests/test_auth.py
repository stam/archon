import requests
import json
import base64
from .testapp.app import app, db
from chimera.test import TestCase, Client, MockResponse, MockWebSocket
from chimera.models import User

subscribe_company = {
    'target': 'company',
    'type': 'subscribe',
}

authenticate = {
    'type': 'authenticate',
    'data': {
        'code': 'foo',
    },
}


def create_fake_google_id_token():
    u_data = {
        'name': 'Henk de Vries',
        'email': 'henk@devries.nl',
        'picture': 'bla',
    }

    body_decoded = json.dumps(u_data)
    body = base64.urlsafe_b64encode(body_decoded.encode())
    # Strip the = from the body to reproduce google's twisted response
    body_malformed = body.decode().split('=')[0]
    return 'foo.{}.bar'.format(body_malformed)


class TestAuth(TestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_unauth_request(self):
        ws = MockWebSocket()
        ws.mock_incoming_message(json.dumps(subscribe_company))
        self.client.open_connection(ws)

        self.assertEqual(1, len(ws.outgoing_messages))
        m = ws.outgoing_messages[0]

        self.assertDictEqual({
            'type': 'subscribe',
            'message': 'unauthorized',
            'code': 'error',
        }, json.loads(m))

    def test_google_oauth(self):
        def mock_oauth(request, **kwargs):
            return MockResponse({
                'id_token': create_fake_google_id_token()
                }, 200)

        self.client.set_mock_api(mock_oauth)
        ws = MockWebSocket()
        ws.mock_incoming_message(json.dumps(authenticate))
        self.client.open_connection(ws)

        self.assertEqual(1, requests.post.call_count)
        # Assert client_id, client_secret, redirect_uri, code, grant_type in request

        users = self.client.db.session.query(User).all()
        self.assertEqual(1, len(users))
        self.assertEqual('henk@devries.nl', users[0].email)

        # TODO Test session token in response and it workss
