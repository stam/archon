import json
from .testapp.app import app, db
from archon.test import LoggedInTestCase, Client, MockWebSocket


class TestCustom(LoggedInTestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_company(self):
        ws = MockWebSocket()
        ws.mock_incoming_message({
            'target': 'company',
            'type': 'ask_for_raise',
        })

        self.client.open_connection(ws)

        self.assertEqual(1, len(ws.outgoing_messages))
        m = ws.outgoing_messages[0]

        self.assertDictEqual({
            'answer': 'no',
            'code': 'error',
        }, json.loads(m))
