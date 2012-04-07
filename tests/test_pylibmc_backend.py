from tests._fixtures import _GenericBackendTest, _GenericMutexTest
from tests import eq_
from unittest import TestCase
from threading import Thread
import time

class PylibmcTest(_GenericBackendTest):
    backend = "dogpile.cache.pylibmc"

    region_args = {
        "key_mangler":lambda x: x.replace(" ", "_")
    }
    config_args = {
        "arguments":{
            "url":"127.0.0.1"
        }
    }

class PylibmcDistributedTest(_GenericBackendTest):
    backend = "dogpile.cache.pylibmc"

    region_args = {
        "key_mangler":lambda x: x.replace(" ", "_")
    }
    config_args = {
        "arguments":{
            "url":"127.0.0.1",
            "distributed_lock":True
        }
    }

class PylibmcDistributedMutexTest(_GenericMutexTest):
    backend = "dogpile.cache.pylibmc"

    config_args = {
        "arguments":{
            "url":"127.0.0.1",
            "distributed_lock":True
        }
    }

from dogpile.cache.backends.memcached import PylibmcBackend
class MockPylibmcBackend(PylibmcBackend):
    def _imports(self):
        pass

    def _create_client(self):
        return MockClient(self.url, 
                        binary=self.binary,
                        behaviors=self.behaviors
                    )

class MockClient(object):
    number_of_clients = 0

    def __init__(self, *arg, **kw):
        self.arg = arg
        self.kw = kw
        self.canary = []
        self._cache = {}
        MockClient.number_of_clients += 1

    def get(self, key):
        return self._cache.get(key)
    def set(self, key, value, **kw):
        self.canary.append(kw)
        self._cache[key] = value
    def delete(self, key):
        self._cache.pop(key, None)
    def __del__(self):
        MockClient.number_of_clients -= 1

class PylibmcArgsTest(TestCase):
    def test_binary_flag(self):
        backend = MockPylibmcBackend(arguments={'url':'foo','binary':True})
        eq_(backend._create_client().kw["binary"], True)

    def test_url_list(self):
        backend = MockPylibmcBackend(arguments={'url':["a", "b", "c"]})
        eq_(backend._create_client().arg[0], ["a", "b", "c"])

    def test_url_scalar(self):
        backend = MockPylibmcBackend(arguments={'url':"foo"})
        eq_(backend._create_client().arg[0], ["foo"])

    def test_behaviors(self):
        backend = MockPylibmcBackend(arguments={'url':"foo", 
                                    "behaviors":{"q":"p"}})
        eq_(backend._create_client().kw["behaviors"], {"q": "p"})

    def test_set_time(self):
        backend = MockPylibmcBackend(arguments={'url':"foo", 
                                "memcached_expire_time":20})
        backend.set("foo", "bar")
        eq_(backend._clients.memcached.canary, [{"time":20}])

    def test_set_min_compress_len(self):
        backend = MockPylibmcBackend(arguments={'url':"foo", 
                                "min_compress_len":20})
        backend.set("foo", "bar")
        eq_(backend._clients.memcached.canary, [{"min_compress_len":20}])

    def test_no_set_args(self):
        backend = MockPylibmcBackend(arguments={'url':"foo"})
        backend.set("foo", "bar")
        eq_(backend._clients.memcached.canary, [{}])

class PylibmcThreadTest(TestCase):
    def setUp(self):
        import gc
        gc.collect()
        eq_(MockClient.number_of_clients, 0)

    def test_client_cleanup_1(self):
        self._test_client_cleanup(1)

    def test_client_cleanup_3(self):
        self._test_client_cleanup(3)

    def test_client_cleanup_10(self):
        self._test_client_cleanup(10)

    def _test_client_cleanup(self, count):
        backend = MockPylibmcBackend(arguments={'url':'foo','binary':True})
        canary = []

        def f():
            backend._clients.memcached
            canary.append(MockClient.number_of_clients)
            time.sleep(.05)

        threads = [Thread(target=f) for i in xrange(count)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        eq_(canary, [i + 2 for i in xrange(count)])
        eq_(MockClient.number_of_clients, 1)


