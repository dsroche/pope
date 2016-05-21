#!/usr/bin/env python3

##################################################################
# This file is part of the POPE implementation.                  #
# Paper at https://eprint.iacr.org/2015/1106                     #
# U.S. Government work product, in the public domain.            #
# Written in 2015 by Daniel S. Roche, roche@usna.edu             #
##################################################################

"""
This file contains test code for benchmarking the networked
POPE implementation using salary data.
This version ONLY runs the oracle over the network.
"""

import argparse
import random
import progbar
import time
import os
import pickle
import sys

from ope import pope
from ope import nworacle
from ope import ciphers
from ope import opec


def convkey(x, left=False, right=False):
    """Turns a numerical salary value into a string preserving comparison."""
    assert not (left and right)
    if left:
        appendix = '0'
    elif right:
        appendix = '9'
    else:
        appendix = '5'
    appendix += ''.join(chr(random.randrange(32,127)) for _ in range(5))
    return "{:0>10.2f}".format(x) + appendix


def get_inserts(datafile):
    data = []
    with open(datafile) as data_in:
        for line in data_in:
            try:
                name, salstring = line.strip().split(',')
                salary = float(salstring)
                data.append((salary, convkey(salary), name))
            except ValueError:
                print("WARNING: invalid read of line:", file=sys.stderr)
                print(line.rstrip(), file=sys.stderr)
    return data

def get_queries(ins, num, size=100):
    qtimes = sorted(random.randrange(len(ins)) for _ in range(num))
    res = {}
    assert len(ins) >= size
    for _ in range(num):
        qtime = random.randrange(len(ins))
        contents = ins[:qtime+1]
        contents.sort()
        startind = random.randrange(len(contents))
        while startind > 0 and contents[startind-1][0] == contents[startind][0]:
            startind -= 1
        endind = min(len(contents) - 1, startind + size - 1)
        while endind+1 < len(contents) and contents[endind+1][0] == contents[endind][0]:
            endind += 1
        start = convkey(contents[startind][0], left=True)
        end = convkey(contents[endind][0] + 0.00, right=True)
        out = [(ck, v) for (k,ck,v) in contents[startind:endind+1]]
        res[qtime] = (start, end, out)
    return res

def main(datafile, queries, passphrase, orc, qfile):
    ins = get_inserts(datafile)
    if qfile:
        if os.path.exists(qfile):
            with open(qfile, 'rb') as qin:
                quer = pickle.load(qin)
            print("Loaded queries from", qfile, file=sys.stderr)
        else:
            quer = get_queries(ins, queries)
            with open(qfile, 'wb') as qout:
                pickle.dump(quer, qout)
            print("Saved queries to", qfile, file=sys.stderr)
    else:
        quer = get_queries(ins, queries)

    crypt = ciphers.AES(passphrase)
    thepope = pope.Pope(orc)
    theopec = opec.OpeClient(thepope, crypt)

    elapsed = -time.time()
    with progbar.ProgressBar(len(ins)) as pbar:
        for (i, (k, ck, v)) in enumerate(ins):
            theopec.insert(ck, v)
            if i in quer:
                ck1, ck2, check = quer[i]
                res = list(theopec.range_search(ck1, ck2))
                assert sorted(res) == sorted(check)
            pbar += 1
    elapsed += time.time()

    print("successfully performed", len(ins), "insertions and", len(quer), "queries", file=sys.stderr)
    print("took", elapsed, "seconds", file=sys.stderr)
    print(elapsed)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Network POPE experiment with only the oracle")
    parser.add_argument('oracle_hostname')
    parser.add_argument('oracle_port', type=int)
    parser.add_argument('passphrase')
    parser.add_argument('datafile', help="csv file with name,salary entries")
    parser.add_argument('queries', nargs='?', type=int, default=[1000],
            help="How many random queries to perform (default 1000)")
    parser.add_argument('-s','--seed', type=int, default=1984,
            help="Seed to use for PRNG to make the random queries")
    parser.add_argument('-f','--queryfile', help="file name to load/store queries")
    args = parser.parse_args()

    random.seed(args.seed)
    print("The seed is", args.seed, file=sys.stderr)

    with nworacle.OracleClient(args.oracle_hostname, args.oracle_port) as orc:
        main(args.datafile, args.queries, args.passphrase, orc, args.queryfile)
