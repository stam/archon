import json
from .testapp.app import app, db
from archon.test import LoggedInTestCase, Client, MockWebSocket, greenlet

save_company = {
    'target': 'company',
    'type': 'save',
    'data': {
        'name': 'Garage',
    },
}

update_company = {
    'target': 'company',
    'type': 'update',
    'data': {
        'name': 'Nailsalon',
        'id': 1,
    },
}

subscribe_company = {
    'requestId': '1234',
    'target': 'company',
    'type': 'subscribe',
}

unsubscribe_company = {
    'requestId': '1234',
    'type': 'unsubscribe',
}


class TestUnsubscribe(LoggedInTestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_stop_receiving_publishes(self):
        ws1 = MockWebSocket()
        ws2 = MockWebSocket()
        ws1.mock_incoming_message(subscribe_company)

        g1 = greenlet(self.client.open_connection)
        g1.switch(ws1, app=self.client.app)

        ws2.mock_incoming_message(save_company)
        g2 = greenlet(self.client.open_connection)
        g2.switch(ws2, app=self.client.app)

        # check ws1 receives publish
        self.assertEqual(2, len(ws1.outgoing_messages))
        self.assertDictEqual({
            'type': 'publish',
            'target': 'company',
            'requestId': '1234',
            'data': {'add': [{
                'id': 1,
                'name': 'Garage'}]}
            }, json.loads(ws1.outgoing_messages[1]))

        ws1.mock_incoming_message(unsubscribe_company)
        g1.switch()

        ws2.mock_incoming_message(update_company)
        g2.switch()
        self.assertEqual(2, len(ws2.outgoing_messages))
        self.assertEqual('success', json.loads(ws2.outgoing_messages[1])['code'])

        # check ws1 does no receives publish
        self.assertEqual(3, len(ws1.outgoing_messages))
        self.assertDictEqual({
            'type': 'unsubscribe',
            'code': 'success',
            'requestId': '1234',
            }, json.loads(ws1.outgoing_messages[2]))
