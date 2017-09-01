import json
from .testapp.app import app, db
from archon.test import LoggedInTestCase, Client, MockWebSocket


save_company = {
    'target': 'company',
    'type': 'save',
    'data': {
        'name': 'CY',
    },
}


class TestSave(LoggedInTestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_save_model(self):
        ws = MockWebSocket()
        ws.mock_incoming_message(save_company)

        self.client.open_connection(ws)

        self.assertEqual(1, len(ws.outgoing_messages))
        m = ws.outgoing_messages[0]

        self.assertDictEqual({
            'type': 'save',
            'target': 'company',
            'code': 'success',
            'data': {
                'id': 1,
                'name': 'CY'
            }
        }, json.loads(m))
