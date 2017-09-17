from .testapp.app import app, db
from archon.test import LoggedInTestCase, TestCase, Client
import json


class TestUnAuth(TestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_unauthorized(self):
        res = self.client.http_client.get('/api/company/foo/')
        self.assertEqual(403, res.status_code)
        self.assertEqual(json.loads(res.data.decode()), {
            'message': 'Unauthorized'})


class TestHttp(LoggedInTestCase):
    # TODO: find a way to extend the flask client get...
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_custom_http_route(self):
        res = self.client.http_client.get(
            '/api/company/foo/',
            query_string={
                'authorization': self.client.auth_token
                })

        self.assertEqual(json.loads(res.data.decode()), {
            'foo': 'bar'})

    def test_uncaught_exception(self):
        res = self.client.http_client.get(
            '/api/company/foo_error/',
            query_string={
                'authorization': self.client.auth_token
                })

        self.assertEqual(500, res.status_code)
        self.assertEqual(json.loads(res.data.decode()), {
            'message': "'CompanyController' object has no attribute 'type'"})
