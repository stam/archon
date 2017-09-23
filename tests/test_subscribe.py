import json
from .testapp.app import app, db
from .testapp.models import Company, Employee
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


subscribe_employee_c1 = {
    'requestId': '5678',
    'target': 'employee',
    'scope': {
        'company': 1,
    },
    'type': 'subscribe',
}


class TestScope(LoggedInTestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_fk(self):
        ws = MockWebSocket()

        c1 = Company({'name': 'Slagerij Henk'})
        c2 = Company({'name': 'Slagerij Pieter'})
        db.session.add(c1)
        db.session.add(c2)
        e1 = Employee({'name': 'Henk'})
        e1.company = c1
        db.session.add(e1)
        db.session.commit()

        ws.mock_incoming_message(subscribe_employee_c1)
        ws.mock_incoming_message({
            'target': 'employee',
            'type': 'save',
            'data': {
                'name': 'Jan',
                'company': c1.id,
            },
        })
        ws.mock_incoming_message({
            'target': 'employee',
            'type': 'save',
            'data': {
                'name': 'Pieter',
                'company': c2.id,
            },
        })

        self.client.open_connection(ws)
        # Subscribe success, publish, save success, save success
        self.assertEqual(4, len(ws.outgoing_messages))
        res_sub = json.loads(ws.outgoing_messages[0])
        res_pub = json.loads(ws.outgoing_messages[1])
        res_sv1 = json.loads(ws.outgoing_messages[2])
        res_sv2 = json.loads(ws.outgoing_messages[3])

        for r in [res_sv1, res_sv2]:
            self.assertEqual('success', r['code'])

        self.assertEqual('Henk', res_sub['data']['add'][0]['name'])
        self.assertEqual('Jan', res_pub['data']['add'][0]['name'])
