import requests
import json
import base64
from .testapp.app import app, db
from archon.test import TestCase, Client, MockResponse, MockWebSocket
from archon.models import User
from greenlet import greenlet


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
        ws.mock_incoming_message(subscribe_company)
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
        ws.mock_incoming_message(authenticate)

        g = greenlet(self.client.open_connection)
        g.switch(ws, app=self.client.app)

        self.assertEqual(1, requests.post.call_count)

        call_params = requests.post.call_args_list[0][1]['params']
        self.assertTrue('client_id' in call_params)
        self.assertTrue('client_secret' in call_params)
        self.assertTrue('redirect_uri' in call_params)
        self.assertTrue(call_params['code'], authenticate['data']['code'])
        self.assertTrue(call_params['grant_type'], 'authorization_code')

        users = self.client.db.session.query(User).all()
        self.assertEqual(1, len(users))
        self.assertEqual('henk@devries.nl', users[0].email)

        self.assertEqual(1, len(ws.outgoing_messages))
        m = json.loads(ws.outgoing_messages[0])
        self.assertEqual('authenticate', m['type'])
        self.assertEqual('success', m['code'])
        self.assertTrue('authorization' in m)

        # Now check that the response auth code actually works
        req_bootstrap = {
            'type': 'bootstrap',
            'authorization': m['authorization'],
        }

        ws.mock_incoming_message(req_bootstrap)
        g.switch()

        self.assertEqual(2, len(ws.outgoing_messages))
        m = json.loads(ws.outgoing_messages[1])
        self.assertEqual('bootstrap', m['type'])
        self.assertEqual('success', m['code'])
        self.assertEqual('Henk de Vries', m['data']['username'])
