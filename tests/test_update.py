import json
from .testapp.app import app, db
from greenlet import greenlet
from archon.test import LoggedInTestCase, Client, MockWebSocket


save_company = {
    'target': 'company',
    'type': 'save',
    'data': {
        'name': 'CY',
    },
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

        c_id = res_save['data']['id']
        update_message = {
            'target': 'company',
            'type': 'update',
            'data': {
                'name': 'CY NL',
                'id': c_id,
            }
        }

        ws.mock_incoming_message(update_message)
        g.switch()

        self.assertEqual(2, len(ws.outgoing_messages))
        res_update = json.loads(ws.outgoing_messages[1])

        self.assertEqual('update', res_update['type'])
        self.assertEqual('company', res_update['target'])
        self.assertEqual('success', res_update['code'])
        self.assertEqual('CY NL', res_update['data']['name'])
        self.assertEqual(c_id, res_update['data']['id'])
