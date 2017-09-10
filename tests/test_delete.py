import json
from .testapp.app import app, db
from .testapp.models import Company
from archon.test import LoggedInTestCase, Client, MockWebSocket

delete_company = {
    'target': 'company',
    'type': 'delete',
}


class TestDelete(LoggedInTestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_delete(self):
        ws = MockWebSocket()

        c = Company({
                'name': 'Slagerij Henk',
            })
        db.session.add(c)
        db.session.commit()

        delete_message = {
            'requestId': '1234',
            'target': 'company',
            'type': 'delete',
            'data': {
                'id': c.id,
            }
        }
        ws.mock_incoming_message(delete_message)

        self.client.open_connection(ws)

        self.assertEqual(1, len(ws.outgoing_messages))
        m = ws.outgoing_messages[0]

        self.assertDictEqual({
            'type': 'delete',
            'target': 'company',
            'requestId': '1234',
            'data': {
                'id': c.id,
                'name': c.name,
            },
            'code': 'success',
        }, json.loads(m))
