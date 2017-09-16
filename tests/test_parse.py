import json
from .testapp.app import app, db
from .testapp.models import Employee, Company
from archon.test import LoggedInTestCase, Client, MockWebSocket, greenlet


save_company = {
    'target': 'company',
    'type': 'save',
    'data': {
        'name': 'Snackbar',
    },
}


class TestParse(LoggedInTestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_save_model(self):
        ws = MockWebSocket()
        ws.mock_incoming_message(save_company)
        g = greenlet(self.client.open_connection)
        g.switch(ws, app=self.client.app)

        self.assertEqual(1, len(ws.outgoing_messages))
        c = json.loads(ws.outgoing_messages[0])['data']

        ws.mock_incoming_message({
            'target': 'employee',
            'type': 'save',
            'data': {
                'name': 'Henk',
                'company': c['id'],
                'started_at': '2017-09-16T15:59:36+02:00',
                'birthday': '1993-03-21',
            },
        })
        g.switch()

        self.assertEqual(2, len(ws.outgoing_messages))
        r2 = json.loads(ws.outgoing_messages[1])
        self.assertDictEqual({
            'target': 'employee',
            'type': 'save',
            'code': 'success',
            'data': {
                'id': 1,
                'name': 'Henk',
                'company': c['id'],
                'started_at': '2017-09-16T13:59:36+00:00',
                'birthday': '1993-03-21',
            },
        }, r2)

        c = Company.query.get(1)
        e = Employee.query.get(1)

        self.assertEqual(e.company, c)
        self.assertEqual(c.employees.first(), e)
