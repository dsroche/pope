#!/usr/bin/env python3

##################################################################
# This file is part of the POPE implementation.                  #
# Paper at https://eprint.iacr.org/2015/1106                     #
# U.S. Government work product, in the public domain.            #
# Written in 2015 by Daniel S. Roche, roche@usna.edu             #
##################################################################

import argparse
import random

from ope.opec import create_ope_client
from ope.ciphers import DumbCipher
from ope.pope import Pope
from ope.mope import Mope
from ope.cheater import Cheater

# some quotes from Alexander Pope
quotes = [
        "Some people will never learn anything, for this reason, because they understand everything too soon.",
        "To be angry is to revenge the faults of others on ourselves.",
        "To err is human; to forgive, divine.",
        "A little learning is a dangerous thing; Drink deep, or taste not the Pierian spring.",
]

def main(OpeClass, sentence):
    """Creates an OPE instance, inserts the given words, and does some
    range query checks."""

    client = create_ope_client(OpeClass, Cipher=DumbCipher, local_size=5)

    # break up the sentence into words that will be inserted
    words = list(map(lambda s: s.lower().strip('.,;'), sentence.split()))
    swords = sorted(words)
    
    # insert each word as the key, and its index as that data/payload.
    for ind, word in enumerate(words):
        client.insert(word, str(ind))

    print("Inserted all words in the sentence:")
    print(sentence)

    # traverse the whole thing
    print()
    print("Full traversal:")
    for word, indstr in client.traverse():
        print("   ", word, indstr)

    # do a range search
    start, end = words[1], words[-1]
    print()
    print("The words between", start, "and", end, "are:")
    for word, indstr in client.range_search(start, end):
        print("   ", word, indstr)
    print("(note: range is inclusive on the left, exclusive on the right)")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description="Small demo of an OPE implementation",)
    parser.add_argument('protocol', nargs='?', default='POPE',
            help="Which construction to use: POPE, mOPE, or Cheater")
    parser.add_argument('--sentence', '-s',  nargs=argparse.REMAINDER,
            help="What sentence of words to insert (default: a Pope quote)")

    args = parser.parse_args()

    if args.protocol.lower() == 'pope':
        print("Testing POPE")
        print()
        alg = Pope
    elif args.protocol.lower() == 'mope':
        print("Testing mOPE")
        print()
        alg = Mope
    elif args.protocol.lower() == 'cheater':
        print("Testing Cheater")
        print()
        alg = Cheater
    else:
        print("ERROR: protocol must be POPE, mOPE, or Cheater")
        exit(1)
    
    if args.sentence is not None:
        sentence = " ".join(args.sentence)
    else:
        sentence = random.choice(quotes)

    main(alg, sentence)
