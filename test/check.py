#!/usr/bin/python3

import sys
import random
import itertools

from ope.opec import OpeClient
from ope.ciphers import DumbCipher, AES
from ope.pope import Pope
from ope.cheater import Cheater
from ope.mope import Mope
from ope.oracle import Oracle

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1].startswith('-'):
        print("Runs some random correctness checks")
        print("Usage:", sys.argv[0], "[size] [seed]")
        exit(1)

    N = int(sys.argv[1]) if len(sys.argv) >= 2 else 1000
    seed = int(sys.argv[2]) if len(sys.argv) >= 3 else random.randrange(100000)

    random.seed(seed)
    print("seed is", seed)

    for algo in (Cheater, Pope, Mope):
        print("Checking {}...".format(algo.__name__))

        ############## small demo here
        # print("=== SMALL DEMO START ===")

        alphabet = [chr(x) for x in range(ord('A'), ord('Z')+1)]
        alphabet = [x+y for x in alphabet for y in alphabet]
        random.shuffle(alphabet)
        ins = alphabet[:150]
        other = alphabet[150:]
        # print("insertions:", ins)

        class EC:
            def __init__(self, key=None):
                pass
            def encode(self, s):
                return 'e' + s
            def decode(self, s):
                assert s.startswith('e')
                return s[1:]

        #cl = client.Client(mem=5, key='e', cipher=EC)
        crypt = DumbCipher('enkey')
        cl = OpeClient(algo(Oracle(crypt, 5)), crypt)

        for s in ins:
            cl.insert(s, s+'v')
        # print("Inserted all", len(ins), "items")
        cl._serv.check(True,True)
        assert cl.size() == len(ins)

        random.shuffle(ins)
        # print("lookups:", ins[:53])

        for s in ins[:53]:
            res = cl.lookup(s)
            assert cl.size() == len(ins)
            assert res == s+'v'
            cl._serv.check(True)
        # print("All 53 lookups worked.")
        cl._serv.check(True,True)

        # print("more lookups:", other[:10])
        for s in other:
            res = cl.lookup(s)
            assert res is None
        # print("All", len(other), "bad lookups worked")
        cl._serv.check(True,True)
        # print()

        ############## big demo here
        # print("=== BIG DEMO START ===")

        wordsfn = '/usr/share/dict/words'

        with open(wordsfn, 'r') as words:
            wordlist = [line.strip() for line in words]
        random.shuffle(wordlist)

        # ensure there are enough words in the list!
        assert len(wordlist) >= 2*N+1

        # pick N random word pairs
        pairs = list(itertools.islice(zip(wordlist, wordlist[::-1]), N))

        # initialize the database and insert the key,value pairs
        crypt = AES()
        cl = OpeClient(algo(Oracle(crypt, 5)), crypt)
        checker = {}
        for (k,v) in pairs:
            cl.insert(k,v)
            checker[k] = v

        assert cl.size() == N
        # print("Finished inserting {} items".format(N))
        cl._serv._cmp.counts_summary(True)
        # print("Tree structure:")
        cl._serv.check(info=True)
        # print()

        nlook = round(N**.5)
        for w in random.sample(wordlist, nlook):
            if w in checker:
                assert cl.lookup(w) == checker[w]
            else:
                assert cl.lookup(w) is None

        # print("Finished checking {} random lookups".format(nlook))
        cl._serv._cmp.counts_summary(True)
        # print("Tree structure:")
        cl._serv.check(info=True)
        # print()

        ranges = [("a","z"), ("alice","bob"), ("from","to"), ("range","empty")]
        for start, end in ranges:
            checkset = sorted((k,checker[k]) for k in checker if start <= k < end)
            res = sorted(cl.range_search(start,end))
            assert res == checkset

        # print("Finished checking {} ranges".format(len(ranges)))
        cl._serv._cmp.counts_summary(True)
        # print("Tree structure:")
        cl._serv.check(info=True)
        # print()

        for w in checker:
            assert cl.lookup(w) == checker[w]

        # print("Finished checking {} successful lookups".format(N))
        cl._serv._cmp.counts_summary(True)
        # print("Tree structure:")
        cl._serv.check(info=True)
        # print()

        print("All checks passed!")
        print()



