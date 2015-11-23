##################################################################
# This file is part of the POPE implementation.                  #
# Paper at https://eprint.iacr.org/2015/1106                     #
# U.S. Government work product, in the public domain.            #
# Written in 2015 by Daniel S. Roche, roche@usna.edu             #
##################################################################

"""
This is the mOPE protocol accodring to
Popa, Li, Zeldovich. "An Ideal-Security Protocol for Order-Preserving 
Encoding". 2013 IEEE Symposium of Security and Privacy,
https://eprint.iacr.org/2013/129
"""

import bisect
import collections

class Mope:
    def __init__(self, oracle):
        self._tree = LeafNode(self, [], [])
        self._cmp = oracle
        self._encodings = []
        self._data = collections.defaultdict(lambda: [])

    def encode(self, key, insert):
        """Does the OPE encoding of the given ciphertext.
        
        insert is True if the key should actually be inserted
        if not found. Otherwise the successor encryption will be
        returned.
        """
        if __debug__: self.check()
        updates = []
        restup, found = self._tree.encode(key, insert, updates)
        res = self._tuptoval(restup)
        if insert and not found:
            upencs = [(self._tuptoval(oldtup), self._tuptoval(newtup))
                      for (oldtup,newtup) in updates]
            upinds = [bisect.bisect_left(self._encodings, old)
                      for (old, _) in upencs]
            updata = []
            for upind, (old, new) in zip(upinds, upencs):
                assert upind < len(self._encodings)
                assert self._encodings[upind] == old
                self._encodings[upind] = new
                updata.append((new, self._data[old]))
                del self._data[old]
            for new, val in updata:
                self._data[new] = val
            ind = bisect.bisect_left(self._encodings, res)
            assert ind == len(self._encodings) or self._encodings[ind] != res
            self._encodings.insert(ind, res)
            assert self._encodings == sorted(self._encodings)
        else:
            ind = bisect.bisect_left(self._encodings, res)
            assert not updates
            assert not found or self._encodings[ind] == res
        if __debug__: self.check(False, False, res if insert else None)
        return res, ind, found

    def insert(self, key, val):
        encoding, ind, _ = self.encode(key, True)
        self._data[encoding].append((key,val))

    def lookup(self, key):
        ekey, _, found = self.encode(key, False)
        if found:
            return self._data[ekey][0][1]
        else:
            return None

    def range_search(self, key1, key2):
        _, ind1, __ = self.encode(key1, False)
        _, ind2, __ = self.encode(key2, False)
        for ii in range(ind1, ind2):
            for res in self._data[self._encodings[ii]]:
                yield res

    def size(self):
        return sum(len(lst) for lst in self._data.values())

    def traverse(self):
        for enc in self._encodings:
            for key_value in self._data[enc]:
                yield key_value

    def _tuptoval(self, tup):
        res = 0
        power = 1
        for x in tup:
            res *= power
            res += x
            power *= (self._tree.maxlen + 1)
        return res

    def check(self, full=False, info=False, inserted=None):
        if info:
            print("mOPE size is", self.size(), "with tree height", self._tree.height())
        intree = list(self._tree.traverse())
        assert all(len(enc) == len(intree[0]) for enc in intree)
        ite = list(self._tuptoval(enc) for enc in intree)
        assert ite == self._encodings
        assert all((x == inserted or self._data[x]) for x in self._encodings)
        assert all(len(lst) == 0 or enc in self._encodings 
                   for enc,lst in self._data.items())
        if full:
            for (ekey, lst) in self._data.items():
                if len(lst) >= 2:
                    fd = self._cmp.crypt.decode(lst[0][0])
                    assert all(self._cmp.crypt.decode(k) == fd for k,v in lst)
            prev = None
            for ekey in self._encodings:
                u = self._cmp.crypt.decode(self._data[ekey][0][0])
                if prev is not None:
                    assert prev < u
                prev = u


class Node:
    maxlen = 4

    def __init__(self, serv, suffix, keys, encs, parent=None):
        self.serv = serv
        self.parent = parent
        self.keys = list(keys)
        self.encs = list(encs)
        if parent:
            self.prefix = None
            self.parind = None
        else:
            self.prefix = ()
            self.parind = 0
        self.suffix = suffix

    def find(self, key):
        [(_, ind)] = self.serv._cmp.find([key], self.keys)
        if ind >= 0:
            return (ind, True)
        else:
            return (-1-ind, False)

    def make_parent(self):
        if self.parent is None:
            assert self.serv._tree == self
            self.serv._tree = self.parent = InternalNode(
                    self.serv, (0,) + self.suffix, [], [], [self])
            self.parind = 0
            self.prefix = (0,)
        return self.parent
    
    def redo_encs(self, updates, start=0):
        inserted = None
        for ind in range(start, len(self.encs)):
            newenc = self.prefix + (ind+1,) + self.suffix
            if self.encs[ind] is None:
                assert inserted is None
                inserted = newenc
            else:
                updates.append((self.encs[ind], newenc))
            self.encs[ind] = newenc
        return inserted


class LeafNode(Node):
    def __init__(self, serv, keys, encs, parent=None):
        super().__init__(serv, (), keys, encs, parent)

    def encode(self, key, insert, updates):
        ind, found = self.find(key)
        if insert and not found:
            self.keys.insert(ind, key)
            self.encs.insert(ind, None)
            if len(self.keys) > self.maxlen:
                split = self.maxlen // 2
                promoted = (self.keys[split], self.encs[split])
                newsib = LeafNode(self.serv, 
                                  self.keys[split+1:],
                                  self.encs[split+1:],
                                  self.make_parent())
                del self.keys[split:]
                del self.encs[split:]
                enc = self.parent.add(self.parind, promoted, newsib, updates)
            else:
                enc = self.redo_encs(updates, ind)
        elif ind < len(self.encs):
            enc = self.encs[ind]
        else:
            enc = self.encs[-1][:-1] + (self.maxlen+1,)
        assert enc is not None
        return enc, found

    def redo_all(self, updates):
        return self.redo_encs(updates)

    def height(self):
        return 0

    def traverse(self):
        assert len(self.keys) == len(self.encs)
        assert self.suffix == ()
        for ii,enc in enumerate(self.encs):
            assert enc == self.prefix + (ii+1,)
            yield enc

class InternalNode(Node):
    def __init__(self, serv, suffix, keys, encs, children, parent=None):
        super().__init__(serv, suffix, keys, encs, parent)
        self.children = list(children)
        assert len(self.children) == len(self.keys)+1

    def encode(self, key, insert, updates):
        (ind, found) = self.find(key)
        if found:
            return (self.encs[ind], True)
        else:
            return self.children[ind].encode(key, insert, updates)

    def add(self, ind, promoted, newchild, updates):
        self.keys.insert(ind, promoted[0])
        self.encs.insert(ind, promoted[1])
        self.children.insert(ind+1, newchild)
        if len(self.keys) > self.maxlen:
            split = self.maxlen // 2
            myprom = (self.keys[split], self.encs[split])
            newsib = InternalNode(self.serv, self.suffix,
                    self.keys[split+1:],
                    self.encs[split+1:],
                    self.children[split+1:],
                    self.make_parent())
            del self.keys[split:]
            del self.encs[split:]
            del self.children[split+1:]
            inserted = self.parent.add(self.parind, myprom, newsib, updates)
        else:
            inserted = self.redo_encs_children(updates, ind)
        assert inserted is not None
        return inserted

    def redo_encs_children(self, updates, start=0):
        inserted = self.redo_encs(updates, start)
        for ii in range(start, len(self.children)):
            self.children[ii].parent = self
            self.children[ii].prefix = self.prefix + (ii,)
            self.children[ii].parind = ii
            cins = self.children[ii].redo_all(updates)
            if cins:
                assert inserted is None
                inserted = cins
        return inserted

    def redo_all(self, updates):
        return self.redo_encs_children(updates)

    def height(self):
        assert all(child.height() == self.children[0].height() 
                   for child in self.children)
        return self.children[0].height() + 1

    def traverse(self):
        assert len(self.children) == 1 + len(self.encs) == 1 + len(self.keys)
        for ii,(child, enc) in enumerate(zip(self.children, self.encs)):
            assert child.parent == self
            assert child.parind == ii
            assert self.suffix == (0,) + child.suffix
            assert child.prefix == self.prefix + (ii,)
            for cenc in child.traverse():
                yield cenc
            assert enc == self.prefix + (ii+1,) + self.suffix
            yield enc
        ii, child = len(self.encs), self.children[-1]
        assert child.parent == self
        assert child.parind == ii
        assert self.suffix == (0,) + child.suffix
        assert child.prefix == self.prefix + (ii,)
        for cenc in child.traverse():
            yield cenc
