import json
from .testapp.app import app, db
from .testapp.models import Company
from greenlet import greenlet
from archon.test import LoggedInTestCase, Client, MockWebSocket


save_company = {
    'target': 'company',
    'type': 'save',
    'data': {
        'name': 'Butcher',
    },
}

update_company = {
    'target': 'company',
    'type': 'update',
    'data': {
        'name': 'Hairdresser',
        'id': 1,
    }
}

subscribe_company = {
    'requestId': '1234',
    'target': 'company',
    'data': {
        'name': 'Hairdresser',
    },
    'type': 'subscribe',
}


class TestUpdate(LoggedInTestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_update_model(self):
        ws = MockWebSocket()
        ws.mock_incoming_message(save_company)

        g = greenlet(self.client.open_connection)
        g.switch(ws, app=self.client.app)

        self.assertEqual(1, len(ws.outgoing_messages))
        res_save = json.loads(ws.outgoing_messages[0])
        self.assertEqual(res_save['code'], 'success')

        ws.mock_incoming_message(update_company)
        g.switch()

        self.assertEqual(2, len(ws.outgoing_messages))
        res_update = json.loads(ws.outgoing_messages[1])

        self.assertEqual('update', res_update['type'])
        self.assertEqual('company', res_update['target'])
        self.assertEqual('success', res_update['code'])
        self.assertEqual('Hairdresser', res_update['data']['name'])
        self.assertEqual(1, res_update['data']['id'])

    def test_fails_without_id(self):
        ws = MockWebSocket()
        ws.mock_incoming_message(save_company)

        g = greenlet(self.client.open_connection)
        g.switch(ws, app=self.client.app)

        self.assertEqual(1, len(ws.outgoing_messages))
        res_save = json.loads(ws.outgoing_messages[0])
        self.assertEqual(res_save['code'], 'success')

        update_no_id = {
            'target': 'company',
            'type': 'update',
            'data': {
                'name': 'Hairdresser',
            }
        }

        ws.mock_incoming_message(update_no_id)
        g.switch()

        self.assertEqual(2, len(ws.outgoing_messages))
        res_update = json.loads(ws.outgoing_messages[1])

        self.assertDictEqual({
            'type': 'update',
            'code': 'error',
            'message': 'No id given',
        }, res_update)


class TestSub(LoggedInTestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_update_into_scope(self):
        ws = MockWebSocket()

        c = Company({
                'name': 'Butcher',
            })
        db.session.add(c)
        db.session.commit()

        ws.mock_incoming_message(subscribe_company)
        ws.mock_incoming_message(update_company)

        self.client.open_connection(ws)

        self.assertEqual(3, len(ws.outgoing_messages))
        r1 = json.loads(ws.outgoing_messages[0])
        r2 = json.loads(ws.outgoing_messages[1])
        r3 = json.loads(ws.outgoing_messages[2])

        self.assertEqual('publish', r1['type'])
        self.assertEqual(0, len(r1['data']['add']))
        self.assertEqual('success', r1['code'])

        self.assertEqual('update', r3['type'])
        self.assertEqual('success', r3['code'])

        self.assertDictEqual({
            'type': 'publish',
            'target': 'company',
            'requestId': '1234',
            'data': {
                'add': [{
                    'id': c.id,
                    'name': c.name,
                }]
            },
        }, r2)

    def test_update_out_of_scope(self):
        ws = MockWebSocket()

        c = Company({
                'name': 'Butcher',
            })
        db.session.add(c)
        db.session.commit()

        subscribe_company = {
            'requestId': '9012',
            'target': 'company',
            'data': {
                'name': 'Butcher',
            },
            'type': 'subscribe',
        }

        ws.mock_incoming_message(subscribe_company)
        ws.mock_incoming_message(update_company)

        self.client.open_connection(ws)

        self.assertEqual(3, len(ws.outgoing_messages))
        r1 = json.loads(ws.outgoing_messages[0])
        r2 = json.loads(ws.outgoing_messages[1])
        r3 = json.loads(ws.outgoing_messages[2])

        self.assertEqual('publish', r1['type'])
        self.assertEqual(1, len(r1['data']['add']))
        self.assertEqual('success', r1['code'])

        self.assertEqual('update', r3['type'])
        self.assertEqual('success', r3['code'])

        self.assertDictEqual({
            'type': 'publish',
            'target': 'company',
            'requestId': '9012',
            'data': {
                'remove': [{
                    'id': c.id,
                    'name': c.name,
                }]
            },
        }, r2)

    def test_update_already_in_scope(self):
        ws = MockWebSocket()

        c = Company({
                'name': 'Butcher',
            })
        db.session.add(c)
        db.session.commit()

        subscribe_company = {
            'requestId': '5678',
            'target': 'company',
            'data': {
                'id': 1,
            },
            'type': 'subscribe',
        }

        ws.mock_incoming_message(subscribe_company)
        ws.mock_incoming_message(update_company)

        self.client.open_connection(ws)

        self.assertEqual(3, len(ws.outgoing_messages))
        r1 = json.loads(ws.outgoing_messages[0])
        r2 = json.loads(ws.outgoing_messages[1])
        r3 = json.loads(ws.outgoing_messages[2])

        self.assertEqual('publish', r1['type'])
        self.assertEqual(1, len(r1['data']['add']))
        self.assertEqual('success', r1['code'])

        self.assertEqual('update', r3['type'])
        self.assertEqual('success', r3['code'])

        self.assertDictEqual({
            'type': 'publish',
            'target': 'company',
            'requestId': '5678',
            'data': {
                'update': [{
                    'id': c.id,
                    'name': c.name,
                }]
            },
        }, r2)
