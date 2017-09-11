from .testapp.app import app, db
from archon.test import TestCase, Client, MockWebSocket


class TestPing(TestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_pong(self):
        ws = MockWebSocket()

        ws.mock_incoming_message('ping')

        self.client.open_connection(ws)

        self.assertEqual(1, len(ws.outgoing_messages))
        # Whoops our response is a json encoded string
        self.assertEqual('pong', ws.outgoing_messages[0])
