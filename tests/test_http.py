from .testapp.app import app, db
from archon.test import TestCase, Client
import json


class TestHttp(TestCase):
    def setUp(self):
        self.client = Client(app, db)
        super().setUp()

    def test_custom_http_route(self):
        res = self.client.http_client.get('/api/company/foo/')
        self.assertEqual(json.loads(res.data.decode()), {
                'foo': 'bar'
            })
