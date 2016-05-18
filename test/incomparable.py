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
import os
import bisect
from PIL import Image # requires pil

from ope.opec import create_ope_client
from ope.ciphers import DumbCipher
from ope.pope import Pope

class RevealedKeys:
    def __init__(self, allkeys):
        self.allkeys = allkeys
        self.keyind = {}
        for ind, (k, ck) in enumerate(self.allkeys):
            self.keyind[ck] = ind
        self.revind = []
        self.revkeys = {}
        self.revck = set()

    def add(self, ck):
        if ck in self.revck:
            return
        self.revck.add(ck)
        ind = self.keyind[ck]
        k, ck2 = self.allkeys[ind]
        assert ck == ck2
        if k in self.revkeys:
            a, b = self.revkeys[k]
            if ind < a:
                for other in range(ind+1, a):
                    self.addind(other)
                    self.revck.add(self.allkeys[other][1])
                self.revkeys[k] = ind, b
            elif ind > b:
                for other in range(b+1, ind):
                    self.addind(other)
                    self.revck.add(self.allkeys[other][1])
                self.revkeys[k] = a, ind
        else:
            self.revkeys[k] = (ind, ind)
        self.addind(ind)

    def addind(self, ind):
        assert ind not in self.revind
        bisect.insort_left(self.revind, ind)



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

def random_query(allkeys, revealed):
    """Selects a uniform random range to query."""
    (a,ac), (b,bc) = sorted(random.sample(allkeys, 2))
    revealed.add(ac)
    revealed.add(bc)
    return a, b + 0.01

def update_revealed(popenode, revealed, client, rct):
    if popenode.height() >= 1:
        # only look at internal nodes
        for ct in popenode.sorted:
            if ct not in rct:
                rct.add(ct)
                revealed.add(client._crypt.decode(ct))
        assert not popenode.buffer
        for child in popenode.children:
            update_revealed(child, revealed, client, rct)

def update_bigimage(row, img, allkeys, revealed):
    """Adds one more row to the image based on what's currently revealed."""
    rimg = Image.new('L', (len(allkeys), 1), 255)
    for col in revealed.revind:
        rimg.putpixel((col,0), 0)
    # TODO remove
    # for col, (_,ck) in enumerate(allkeys):
    #     if ck in revealed:
    #         rimg.putpixel((col,0), 0)
    rimg = rimg.resize((img.size[0], 1), Image.BILINEAR)
    img.paste(rimg, (0,row))

def make_sqimage(dim, allkeys, revealed):
    """Makes a square image to show what's comparable and not."""
    n = len(allkeys)
    img = Image.new('L', (dim, n), 128)
    rimg = Image.new('L', (n-1, 1), 0)
    # TODO remove
    # comps = []
    # for ind, (_,ck) in enumerate(allkeys):
    #     if ck in revealed:
    #         comps.append(ind)
    row = 0
    prevind = 0
    for ind in revealed.revind:
        for col in range(prevind, ind):
            rimg.putpixel((col,0), 127)
        rcomp = rimg.resize((dim,1), Image.BILINEAR)
        while row < ind:
            img.paste(rcomp, (0,row))
            row += 1
        for col in range(prevind, ind):
            rimg.putpixel((col,0), 255)
        img.paste(rimg.resize((dim,1), Image.BILINEAR), (0,row))
        row += 1
        prevind = ind
    for col in range(prevind, n-1):
        rimg.putpixel((col,0), 127)
    rcomp = rimg.resize((dim,1), Image.BILINEAR)
    while row < n:
        img.paste(rcomp, (0,row))
        row += 1
    return img.resize((dim,dim), Image.BILINEAR)

def main(datafile, num_queries, image_dims, imfile):
    """Creates a POPE instance, inserts everything from the data file,
    then performs some random queries and makes an image showing the
    growth of comparable elements."""

    # process output file name
    if imfile is not None:
        imfroot, imfext = os.path.splitext(imfile)
        if imfext == '':
            imfext = 'png'

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

    print("Successfully read {:,} entries from {}".format(len(data), datafile))

    # create POPE instance and insert all values
    client = create_ope_client(Pope, Cipher=DumbCipher, local_size=32)

    # extract and sort key values for use in generating random queries
    allkeys = []
    for k, v in data:
        ck = convkey(k)
        client.insert(ck, v)
        allkeys.append((k, ck))
    allkeys.sort()

    print("Successfully inserted {:,} entries into POPE".format(len(data)))

    # perform random range queries and collect data
    revealed = RevealedKeys(allkeys)
    rct = set()
    img = Image.new('L', (image_dims[0], num_queries[-1]+1), 127)
    count = 0

    update_bigimage(count, img, allkeys, revealed)

    while count < num_queries[-1]:
        print(".", end='')
        sys.stdout.flush()
        a, b = random_query(allkeys, revealed)
        akey = client._crypt.encode(convkey(a, left=True))
        bkey = client._crypt.encode(convkey(b, right=True))
        client._serv.range_search(akey, bkey)
        count += 1
        update_revealed(client._serv._root, revealed, client, rct)
        update_bigimage(count, img, allkeys, revealed)
        if count in num_queries:
            sqim = make_sqimage(min(image_dims), allkeys, revealed)
            aim = img.crop((0, 0, image_dims[0], count))
            aim = aim.resize(image_dims, Image.NEAREST)
            print("\nGenerated images for count", count)
            if imfile:
                sqim.save(imfroot + '-sqr-' + str(count) + '.' + imfext)
                aim.save(imfroot + '-all-' + str(count) + ',' + imfext)
            else:
                sqim.show()
                aim.show()

    print("Performed {} random range queries".format(count))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
            description="Incomparable elements experiment",)
    parser.add_argument('datafile', help="csv file with name,salary entries")
    parser.add_argument('queries', nargs='*', type=int, default=[1000],
            help="How many random queries to perform, and when to draw squares (default 1000)")
    parser.add_argument('--width', '-w', default=1024,
            help="Image width in pixels (default 1024)"),
    parser.add_argument('--height', '-H', default=768,
            help="Image height in pixels (default 768)")
    parser.add_argument('--output', '-o', default=None,
            help="Filename to save the image to (default just display)")

    args = parser.parse_args()

    main(args.datafile, sorted(args.queries), (args.width, args.height), args.output)
