import json
from .testapp.app import app, db
from .testapp.models import Company
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


class TestSubscribe(LoggedInTestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_publishes_existing_collection_upon_subscription(self):
        ws = MockWebSocket()
        ws.mock_incoming_message(subscribe_company)

        c = Company({
                'name': 'Slagerij Henk',
            })
        db.session.add(c)
        db.session.commit()

        self.client.open_connection(ws)

        self.assertEqual(1, len(ws.outgoing_messages))
        m = ws.outgoing_messages[0]

        self.assertDictEqual({
            'type': 'publish',
            'target': 'company',
            'requestId': '1234',
            'data': {
                'add': [{
                    'id': c.id,
                    'name': c.name,
                    'type': 'notIT',
                }],
                'update': [],
                'delete': [],
            },
            'code': 'success',
        }, json.loads(m))
