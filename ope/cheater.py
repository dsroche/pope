##################################################################
# This file is part of the POPE implementation.                  #
# Paper at https://eprint.iacr.org/2015/1106                     #
# U.S. Government work product, in the public domain.            #
# Written in 2015 by Daniel S. Roche, roche@usna.edu             #
##################################################################

"""
This is a "cheater" replacement for POPE which just decrypts stuff
and stores it in unsorted order. Used to check correctness.
"""

import bisect
import heapq
import itertools

class Cheater:
    noop = False # set to true to make all operations do nothing

    def __init__(self, oracle):
        self.slst = []
        self.ulst = []
        self._cmp = oracle
        self.crypt = oracle.crypt
        self.sampval = None

    def insert(self, key, val):
        if self.noop:
            return
        ukey = self.crypt.decode(key)
        self.ulst.append((ukey,key,val))
        if not self.sampval:
            self.sampval = type(val)()

    def lookup(self, key):
        if self.noop:
            return None
        ukey = self.crypt.decode(key)
        if self.ulst:
            self.ulst.sort()
            self.slst = list(heapq.merge(self.slst, self.ulst))
            self.ulst = []
        ind = bisect.bisect_left(self.slst, (ukey,key,self.sampval))
        if ind < len(self.slst) and self.slst[ind][0] == ukey:
            return self.slst[ind][2]
        else:
            return None

    def range_search(self, key1, key2):
        if self.noop:
            return ()
        uk1 = self.crypt.decode(key1)
        uk2 = self.crypt.decode(key2)
        if self.ulst:
            self.ulst.sort()
            self.slst = list(heapq.merge(self.slst, self.ulst))
            self.ulst = []
        ind1 = bisect.bisect_left(self.slst, (uk1,key1,self.sampval))
        ind2 = bisect.bisect_right(self.slst, (uk2,key2,self.sampval))
        return ((k,v) for (uk,k,v) in itertools.islice(self.slst, ind1, ind2))

    def size(self):
        return len(self.slst) + len(self.ulst)

    def traverse(self):
        for (ukey, key, val) in self.slst:
            yield (key,val)
        for (ukey, key, val) in self.ulst:
            yield (key,val)

    def check(self, full=False, info=False):
        if info:
            print("Cheater size is", self.size())
