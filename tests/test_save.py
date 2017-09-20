import json
from .testapp.app import app, db
from archon.test import LoggedInTestCase, Client, MockWebSocket


save_company = {
    'target': 'company',
    'type': 'save',
    'data': {
        'name': 'Snackbar',
    },
}

subscribe_company = {
    'requestId': '1234',
    'target': 'company',
    'type': 'subscribe',
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
                'name': 'Snackbar',
                'type': 'notIT',
            }
        }, json.loads(m))


class TestSub(LoggedInTestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_save(self):
        ws = MockWebSocket()

        ws.mock_incoming_message(subscribe_company)
        ws.mock_incoming_message(save_company)

        self.client.open_connection(ws)

        self.assertEqual(3, len(ws.outgoing_messages))
        r1 = json.loads(ws.outgoing_messages[0])
        r2 = json.loads(ws.outgoing_messages[1])
        r3 = json.loads(ws.outgoing_messages[2])

        self.assertEqual('publish', r1['type'])
        self.assertEqual('success', r1['code'])

        self.assertEqual('save', r3['type'])
        self.assertEqual('success', r3['code'])

        self.assertDictEqual({
            'type': 'publish',
            'target': 'company',
            'requestId': '1234',
            'data': {
                'add': [{
                    'id': 1,
                    'name': 'Snackbar',
                    'type': 'notIT',
                }]
            },
        }, r2)
