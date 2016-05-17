#!/usr/bin/env python3

##################################################################
# This file is part of the POPE implementation.                  #
# Paper at https://eprint.iacr.org/2015/1106                     #
# U.S. Government work product, in the public domain.            #
# Written in 2015 by Daniel S. Roche, roche@usna.edu             #
##################################################################

import argparse
import random
import sys

from ope.opec import create_ope_client
from ope.ciphers import DumbCipher
from ope.pope import Pope

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

def random_query(allkeys):
    """Selects a uniform random range to query."""
    a, b = sorted(random.sample(allkeys, 2))
    return a, b #+ 0.01

def get_incomp(client):
    """Computes a list of True/False for which elements are incomparable."""
    return []

def main(datafile, num_queries, image_dims):
    global data, allkeys, client, a, b # FIXME debugging; remove
    # random.seed(1985) # FIXME
    """Creates a POPE instance, inserts everything from the data file,
    then performs some random queries and makes an image showing the
    growth of comparable elements."""

    # read data into a list of (key, value) pairs
    data = []
    with open(datafile) as data_in:
        for line in data_in:
            try:
                name, salstring = line.strip().split(',')
                salary = float(salstring)
                data.append((salary, name))
            except ValueError:
                print("WARNING: invalid read of line:")
                print(line.rstrip())

    # extract and sort key values for use in generating random queries
    allkeys = sorted(k for k,v in data)

    print("Successfully read {:,} entries from {}".format(len(data), datafile))

    # create POPE instance and insert all values
    client = create_ope_client(Pope, Cipher=DumbCipher, local_size=32)

    for k, v in data:
        client.insert(convkey(k), v)

    print("Successfully inserted {:,} entries into POPE".format(len(data)))

    # perform random range queries and collect data
    incomp = []

    for ind in range(num_queries):
        print(".", end="")
        sys.stdout.flush()
        a, b = random_query(allkeys)
        client.range_search(convkey(a,left=True), convkey(b,right=True))
        incomp.append(get_incomp(client))

    print("Performed {} random range queries".format(num_queries))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description="Incomparable elements experiment",)
    parser.add_argument('datafile', help="csv file with name,salary entries")
    parser.add_argument('queries', nargs='?', type=int, default=1000,
            help="How many random queries to perform (default 1000)")
    parser.add_argument('--width', '-w', default=1024,
            help="Image width in pixels (default 1024)"),
    parser.add_argument('--height', '-H', default=768,
            help="Image height in pixels (default 768)")

    args = parser.parse_args()

    main(args.datafile, args.queries, (args.width, args.height))
