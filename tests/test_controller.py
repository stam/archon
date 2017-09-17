import json
from .testapp.app import app, db
from .testapp.models import Company, Employee
from archon.test import LoggedInTestCase, TestCase, Client, MockWebSocket


class TestCustom(LoggedInTestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_company(self):
        ws = MockWebSocket()
        ws.mock_incoming_message({
            'target': 'company',
            'type': 'ask_for_raise',
        })

        self.client.open_connection(ws)

        self.assertEqual(1, len(ws.outgoing_messages))
        m = ws.outgoing_messages[0]

        self.assertDictEqual({
            'answer': 'no',
            'code': 'error',
        }, json.loads(m))

    def test_db_connection(self):
        c = Company({'name': 'Post office'})
        db.session.add(c)
        e1 = Employee({'name': 'Henk'})
        e2 = Employee({'name': 'Peter'})
        e1.company = c
        e2.company = c
        db.session.add(e1, e2)
        db.session.commit()

        ws = MockWebSocket()
        ws.mock_incoming_message({
            'target': 'company',
            'data': {'id': 1},
            'type': 'list_employees',
        })
        self.client.open_connection(ws)

        self.assertEqual(1, len(ws.outgoing_messages))
        m = ws.outgoing_messages[0]

        self.assertDictEqual({
            'code': 'success',
            'data': ['Henk', 'Peter'],
            'type': 'list_employees',
        }, json.loads(m))

    def test_exception(self):
        ws = MockWebSocket()
        ws.mock_incoming_message({
            'target': 'company',
            'data': {'id': 1},
            'type': 'list_employees_error',
        })
        self.client.open_connection(ws)

        self.assertEqual(1, len(ws.outgoing_messages))
        m = ws.outgoing_messages[0]

        self.assertDictEqual({
            'code': 'error',
            'type': 'list_employees_error',
            'message': "'CompanyController' object has no attribute 'type'",
            }, json.loads(m))


class TestNotAuth(TestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_company(self):
        ws = MockWebSocket()
        ws.mock_incoming_message({
            'target': 'company',
            'type': 'ask_for_raise',
        })

        self.client.open_connection(ws)

        self.assertEqual(1, len(ws.outgoing_messages))
        m = ws.outgoing_messages[0]

        self.assertDictEqual({
            'code': 'error',
            'message': 'Unauthorized',
            'type': 'ask_for_raise',
        }, json.loads(m))
