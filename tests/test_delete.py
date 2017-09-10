import json
from .testapp.app import app, db
from .testapp.models import Company
from archon.test import LoggedInTestCase, Client, MockWebSocket

subscribe_company = {
    'requestId': '1234',
    'target': 'company',
    'type': 'subscribe',
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


class TestSub(LoggedInTestCase):
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
        ws.mock_incoming_message(subscribe_company)
        ws.mock_incoming_message(delete_message)

        self.client.open_connection(ws)

        self.assertEqual(3, len(ws.outgoing_messages))
        r1 = json.loads(ws.outgoing_messages[0])
        r2 = json.loads(ws.outgoing_messages[1])
        r3 = json.loads(ws.outgoing_messages[2])

        self.assertEqual('publish', r1['type'])
        self.assertEqual(1, len(r1['data']['add']))
        self.assertEqual('success', r1['code'])

        self.assertEqual('delete', r3['type'])
        self.assertEqual('success', r3['code'])

        self.assertDictEqual({
            'type': 'publish',
            'target': 'company',
            'requestId': '1234',
            'data': {
                'remove': [{
                    'id': c.id,
                    'name': c.name,
                }]
            },
        }, r2)
