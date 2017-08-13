import requests
import json
from .testapp.app import app
from chimera.test import TestCase, Client, MockResponse, MockWebSocket

subscribe_company = {
    'target': 'company',
    'type': 'subscribe',
}


class TestAuth(TestCase):
    def setUp(self):
        self.client = Client(app)

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
