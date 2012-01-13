""" LRU caching class and decorator """

import threading

try:
    range = xrange
except NameError: # pragma: no cover
    pass

_marker = object()

class LRUCache(object):
    def __init__(self, size):
        """ Implements a psueudo-LRU algorithm (CLOCK) """
        if size < 1:
            raise ValueError('size must be >1')
        self.size = size
        self.lock = threading.Lock()
        self.hand = 0
        self.maxpos = size - 1
        self.clock_keys = None
        self.clock_refs = None
        self.data = None
        self.clear()

    def clear(self):
        self.lock.acquire()
        try:
            size = self.size
            self.clock_keys = [_marker] * size
            self.clock_refs = [False] * size
            self.hand = 0
            self.data = {}
        finally:
            self.lock.release()

    def get(self, key, default=None):
        try:
            pos, val = self.data[key]
        except KeyError:
            return default
        self.clock_refs[pos] = True
        return val

    def put(self, key, val, _marker=_marker):
        hand = self.hand
        maxpos = self.maxpos
        clock_refs = self.clock_refs
        clock_keys = self.clock_keys
        data = self.data
        lock = self.lock

        entry = self.data.get(key)
        if entry is not None:
            lock.acquire()
            try:
                # We already have key. Only make sure data is up to date and to
                # remember that it was used.
                pos, old_val = entry
                if old_val is not val:
                    data[key] = (pos, val)
                self.clock_refs[pos] = True
                return
            finally:
                lock.release()

        while 1:
            ref = clock_refs[hand]
            if ref == True:
                clock_refs[hand] = False
                hand = hand + 1
                if hand > maxpos:
                    hand = 0
            else:
                lock.acquire()
                try:
                    oldkey = clock_keys[hand]
                    if oldkey in data:
                        del data[oldkey]
                    clock_keys[hand] = key
                    clock_refs[hand] = True
                    data[key] = (hand, val)
                    hand += 1
                    if hand > maxpos:
                        hand = 0
                    self.hand = hand
                finally:
                    lock.release()
                break

class lru_cache(object):
    """ Decorator for LRU-cached function """
    def __init__(self, maxsize, cache=None): # cache is an arg to serve tests
        if cache is None:
            cache = LRUCache(maxsize)
        self.cache = cache

    def __call__(self, f):
        cache = self.cache
        marker = _marker
        def lru_cached(*arg):
            val = cache.get(arg, marker)
            if val is marker:
                val = f(*arg)
                cache.put(arg, val)
            return val
        lru_cached.__module__ = f.__module__
        lru_cached.__name__ = f.__name__
        lru_cached.__doc__ = f.__doc__
        return lru_cached
