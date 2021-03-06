import json
import redis

from unittest import TestCase
from PersistenceExtensions.Redis import Persister

class TestPersisterRedis(TestCase):
    def setUp(self):
        self.p = Persister(
            host="foobar", 
            port=6379, 
            db=0
        )

    def test_rp_noredis_host(self):
        with self.assertRaises(KeyError):
            self.p.save(key="foo", jsonstr="bar")

    def test_rp_bad_save(self):
        with self.assertRaises(KeyError):
            self.p.save(key="foo",jsonstr="bar")

    def test_rp_bad_load(self):
        with self.assertRaises(KeyError):
            self.p.load(key="foo")
