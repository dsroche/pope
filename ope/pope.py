#!/usr/bin/env python3

"""
The POPE represents an encrypted key/value store that supports
range queries, where the order of the ciphertext keys is revealed
to the the server. The data structure itself is based on buffer
trees, and comparisons are only performed on search operations.
The performance is best when the number of insertions vastly outnumbers
the number of range queries.

Authored 2015 by Daniel S. Roche; US Government work in the public domain.
"""

import random
import itertools

class Pope:
    """Abstraction for the cloud database server. Can perform lookups,
    insertions, and range searches on encrypted keys, provided an
    oracle to partition and sort ciphertexts."""

    def __init__(self, oracle):
        """Creates a new, initially empty, storage backend, relying
        on the given comparison oracle.
        """

        self._cmp = oracle
        self._tsize = self._cmp.max_size
        self._root = LeafNode(self, None)

    def insert(self, key, val):
        assert val is not None
        self._root.insert(key, val)

    def split(self, keys, in_order=False):
        """Prepares to search for any of the keys in the given list.

        After this, a lookup or range search for any of those keys will
        only cost O(height).
        Returns a list of (label, leaf node) tuples.
        """
        # can only deal in size-L chunks.
        assert len(keys) <= self._tsize
        if not in_order and len(keys) > 1:
            keys = self._cmp.sort(keys)
        splits = list(self._root.split(keys))
        for _, leaf in splits:
            if leaf.parent:
                leaf.parent.rebalance()
        return splits

    def lookup(self, key):
        """Returns the corresponding value, or None if not found."""
        [(_, leaf)] = self.split([key], True)
        return leaf.lookup(key)
    
    def range_search(self, key1, key2):
        [(_1, node1), (_2, node2)] = self.split([key1,key2], True)
        # left_ind and right_ind are the actual keys at the leaf level.
        # at higher levels, they are child nodes.
        left_ind, right_ind = key1, key2
        result = []
        while node1 != node2:
            assert node1 is not None and node2 is not None
            result.extend(node1.range_right(key1))
            result.extend(node2.range_left(key2))
            key1, key2 = node1, node2
            node1, node2 = node1.parent, node2.parent
        result.extend(node1.range_search(key1, key2))
        return result

    def size(self):
        return self._root.size()

    def height(self):
        return self._root.height()
    
    def num_nodes(self):
        return self._root.num_nodes()

    def traverse(self):
        return self._root.traverse()

    def check(self, full=False, info=False):
        """For debugging. Check structure is valid.
        If full==True, also do comparisons to check the order.
        If info==True, also print some information about the size.
        """
        sizes = [[0,0,0] for _ in range(self._root.height()+1)]
        self._root.check(sizes, 0, full)
        if info:
            for (i,(nodes, ss, bs)) in enumerate(sizes):
                print("level {}: {} nodes, {} sorted, {} buffers".format(i,nodes,ss,bs))
            tn,ts,bs = (sum(L) for L in zip(*sizes))
            print("TOTAL: {} nodes, {} sorted, {} buffers".format(tn,ts,bs))

class LeafNode:
    """Leaf node of the B tree. Contains the values as well as the keys."""

    def __init__(self, serv, parent, buffer_list=None):
        """serv is the Pope object that contains this node."""
        self.serv = serv
        self.parent = parent
        self.buffer = buffer_list if buffer_list else []
        
    def size(self):
        return len(self.buffer)

    def height(self):
        return 0

    def num_nodes(self):
        return 1
    
    def insert(self, key, val):
        """Inserts the given (key,value) pair into the buffer."""
        assert val is not None
        self.buffer.append((key,val))

    def lookup(self, key):
        """Returns the corresponding value, or None if not found."""
        assert len(self.buffer) <= self.serv._tsize
        [(_, ind)] = self.serv._cmp.find([key], self.buffer, haykey=first)
        return self.buffer[ind][1] if ind >= 0 else None

    def range_search(self, key1, key2):
        """Iterates through all (key,value) pairs in the range key1 <= key <= key2."""
        assert len(self.buffer) <= self.serv._tsize
        self.buffer, [(_1, ind1), (_2, ind2)] = self.serv._cmp.partition_sort(
            [key1,key2], self.buffer, haykey=first)
        return self.buffer[ind1: ind2]
            
    def range_right(self, key1):
        """Iterates through all (key,value) pairs satisfying key >= key1."""
        assert len(self.buffer) <= self.serv._tsize
        self.buffer, [(_,ind1)] = self.serv._cmp.partition_sort(
            [key1], self.buffer, haykey=first)
        return self.buffer[ind1:]
        
    def range_left(self, key2):
        """Iterates through all (key,value) pairs satisfying key <= key2."""
        assert len(self.buffer) <= self.serv._tsize
        self.buffer, [(_,ind2)] = self.serv._cmp.partition_sort(
            [key2], self.buffer, haykey=first)
        return self.buffer[:ind2]

    def traverse(self):
        """Iterates through all (key,value) pairs."""
        return self.buffer

    def split(self, keys):
        """Clears the buffer (by sorting it, possibly causing splits etc)
        so that the given keys can be searched without any further clean-up
        operations.
        Note: keys should already be sorted.
        """
        assert len(keys) <= self.serv._tsize
        result = []
        while keys and self.size() > self.serv._tsize:
            # do an L-way split
            # select L random keys to promote, sort them,
            # and partition everything according to those keys
            promoted, partitions = self.serv._cmp.partition_sort(
                itertools.chain(self.buffer, ((k,None) for k in keys)),
                (k for k,v in random.sample(self.buffer, self.serv._tsize)),
                nkey=first
            )
            # bucket[i] holds the key/value pairs for that new node.
            buckets = [[] for _ in range(len(promoted)+1)]
            key_buckets = [[] for _ in range(len(promoted)+1)]
            for (k,v), ind in partitions:
                if v is None:
                    # k is a search key
                    key_buckets[ind].append(k)
                else:
                    # (k,v) was in the buffer
                    buckets[ind].append((k,v))
            # eliminate empty nodes at the end
            while not buckets[-1]:
                # the last promoted value was the last key in order.
                del buckets[-1]
                key_buckets[-2].extend(key_buckets[-1])
                del key_buckets[-1]
                del promoted[-1]
            assert all(bucket for bucket in buckets)
            assert len(buckets) == len(key_buckets) == len(promoted)+1
            # Grow a new root node if necessary
            if self.parent is None:
                assert self.serv._root == self
                self.serv._root = self.parent = InternalNode(self.serv, self)
            # Create new nodes and recurse as necessary
            for bucket, bkeys, pkey in zip(buckets[:-1], key_buckets[:-1], promoted):
                newnode = LeafNode(self.serv, self.parent, buffer_list=bucket)
                self.parent.insert_child_left(newnode, pkey, self)
                if bkeys:
                    result.extend(newnode.split(bkeys))
            # this node will be from the final bucket.
            self.buffer = buckets[-1]
            keys = key_buckets[-1]
        if keys:
            assert len(self.buffer) <= self.serv._tsize
            result.extend((k,self) for k in keys)
        return result

    def check(self, sizes, depth, full):
        """For debugging. Check structure is valid.
        sizes is a list of (# nodes, total sorted, total buffers) for each depth.
        depth is the depth of this node.
        If full==True, also do comparisons to check the order.
        Returned is the span/range of the node.
        """
        if depth:
            assert self.parent is not None and self.serv._root is not self
            assert self.size() >= 1
        else:
            assert self.parent is None and self.serv._root is self
        assert depth == len(sizes)-1
        sizes[depth][0] += 1
        sizes[depth][2] += len(self.buffer)
        if full:
            bu = [self.serv._cmp.crypt.decode(x) for x,y in self.buffer]
            return min(bu), max(bu)
        else:
            return (None,None)

    def info(self):
        bu = [self.serv._cmp.crypt.decode(x) for x,y in self.buffer]
        return "Leaf node, buf size {}, range {} to {}".format(
                len(self.buffer),
                min(bu),
                max(bu))


class InternalNode:
    """Non-leaf node of the B tree. The "sorted" array is the B-tree node
    and contains keys only. The "buffer" is an unsorted array of key,value
    pairs.
    Invariants: 
        len(self.children) == len(self.sorted) + 1
        and
        all(all(k1 <= self.sorted[i] < k2 
                for k1,v1 in self.children[i].traverse()
                for k2,v2 in self.children[i+1].traverse())
            for i in range(len(self.sorted)))

    """

    def __init__(self, serv, child=None, 
                 parent=None, sorted_list=None, children_list=None):
        """Creates a new internal node with no parent and one child
        (if child is not None), or with parent, sorted array, and children
        as specified (if child is None).
        """
        self.serv = serv
        self.parent = parent
        self.buffer = []
        if child is None:
            assert len(children_list) == len(sorted_list) + 1
            self.sorted = sorted_list
            self.children = children_list
            for child in self.children:
                child.parent = self
        else:
            assert sorted_list is None and children_list is None
            self.sorted = []
            self.children = [child]

    def size(self):
        return len(self.buffer) + sum(child.size() for child in self.children)

    def height(self):
        ch = self.children[0].height()
        assert all(child.height() == ch for child in self.children)
        return ch+1

    def num_nodes(self):
        return 1 + sum(child.num_nodes() for child in self.children)

    def insert(self, key, val):
        """Inserts the (key,value) pair into the buffer."""
        assert val is not None
        self.buffer.append((key,val))

    def range_search(self, child1, child2):
        """Iterates through all (key,value) pairs stored between
        child1 and child2, exclusive."""
        assert not self.buffer
        try:
            ind1 = self.children.index(child1)
            ind2 = self.children.index(child2)
        except ValueError:
            raise ValueError("child not found under this node")
        for child in self.children[ind1+1:ind2]:
            for item in child.traverse():
                yield item

    def range_right(self, child1):
        """Iterates through all (key,value) pairs stored to the left 
        of child2."""
        assert not self.buffer
        try:
            ind1 = self.children.index(child1)
        except ValueError:
            raise ValueError("child not found under this node")
        for child in self.children[ind1+1:]:
            for item in child.traverse():
                yield item

    def range_left(self, child2):
        """Iterates through all (key,value) pairs stored to the left 
        of child2."""
        assert not self.buffer
        try:
            ind2 = self.children.index(child2)
        except ValueError:
            raise ValueError("child not found under this node")
        for child in self.children[:ind2]:
            for item in child.traverse():
                yield item

    def traverse(self):
        """Iterates through all (key,value) pairs."""
        for item in self.buffer:
            yield item
        for child in self.children:
            for item in child.traverse():
                yield item

    def split(self, keys):
        """Clears the buffer (by sorting it, possibly causing splits etc)
        so that the given keys can be searched without any further clean-up
        operations.
        Note: keys should already be sorted.
        """
        assert len(keys) <= self.serv._tsize
        assert 1 <= len(self.sorted) <= self.serv._tsize
        if keys:
            # partition everything according to the sorted keys, by
            # loading the entire sorted list onto the client
            # key_buckets[i] holds the keys that go to child i
            key_buckets = [[] for _ in range(len(self.sorted)+1)]
            for (k,v), ind in self.serv._cmp.partition(
                    itertools.chain(self.buffer, ((k,None) for k in keys)),
                    self.sorted, nkey=first):
                if v is None:
                    # k is a search key
                    key_buckets[ind].append(k)
                else:
                    # (k,v) was in the buffer
                    self.children[ind].insert(k,v)
            del self.buffer[:]
            # recurse on the children that have some of the keys
            assert len(key_buckets) == len(self.children)
            workon = []
            for child, ckeys in zip(self.children, key_buckets):
                if ckeys:
                    workon.append((child,ckeys))
            return itertools.chain.from_iterable(child.split(ckeys)
                for child,ckeys in workon)
        else: 
            return []

    def insert_child_left(self, newnode, split_key, curnode):
        """Inserts newnode to the left of curnode, with split_key between them."""
        try:
            ind = self.children.index(curnode)
        except ValueError:
            raise ValueError("curnode not found under this node")
        self.sorted.insert(ind, split_key)
        self.children.insert(ind, newnode)

    def rebalance(self):
        """Ensures that len(self.sorted) <= L, by splitting if necessary.
        Does not require any comparisons.
        """
        assert not self.buffer
        while len(self.sorted) > 2*self.serv._tsize:
            self.split_off(self.serv._tsize // 2)
        if len(self.sorted) > self.serv._tsize:
            self.split_off(len(self.sorted) // 2)
        if self.parent is not None:
            self.parent.rebalance()
            assert self.serv._tsize // 2 <= len(self.sorted)
        assert 1 <= len(self.sorted) <= self.serv._tsize

    def split_off(self, n):
        """Removes the first n elements into a new, adjacent node.
        (Helper method for rebalance.)"""
        assert n <= self.serv._tsize
        if self.parent is None:
            assert self.serv._root == self
            self.serv._root = self.parent = InternalNode(self.serv, self)
        newnode = InternalNode(self.serv, parent=self.parent, 
                               sorted_list=self.sorted[:n],
                               children_list=self.children[:n+1])
        split_key = self.sorted[n]
        del self.sorted[:n+1]
        del self.children[:n+1]
        self.parent.insert_child_left(newnode, split_key, self)

    def check(self, sizes, depth, full):
        """For debugging. Check structure is valid.
        sizes is a list of (# nodes, total sorted, total buffers) for each depth.
        depth is the depth of this node.
        If full==True, also do comparisons to check the order.
        Returned is the span/range of the node.
        """
        if depth:
            assert self.parent is not None and self.serv._root is not self
            assert len(self.sorted) >= self.serv._tsize // 2
        else:
            assert self.parent is None and self.serv._root is self
            assert len(self.sorted) >= 1
        sizes[depth][0] += 1
        sizes[depth][1] += len(self.sorted)
        sizes[depth][2] += len(self.buffer)
        assert len(self.sorted) <= self.serv._tsize
        for child in self.children:
            assert child.parent == self
        rec = [child.check(sizes,depth+1,full) for child in self.children]
        if full:
            su = [self.serv._cmp.crypt.decode(x) for x in self.sorted]
            bu = [self.serv._cmp.crypt.decode(x) for x,y in self.buffer]
            assert sorted(su) == su
            for i,s in enumerate(su):
                assert rec[i][1] <= s < rec[i+1][0]
            if bu:
                return min(rec[0][0], min(bu)), max(rec[-1][1], max(bu))
            else:
                return rec[0][0], rec[-1][1]
        else:
            return (None,None)

    def info(self):
        su = [self.serv._cmp.crypt.decode(x) for x in self.sorted]
        bu = [self.serv._cmp.crypt.decode(x) for x,y in self.buffer]
        return "Internal node, sorted size {}, buf size {}, range {} to {}".format(
                len(self.sorted),
                len(self.buffer),
                min(su+bu),
                max(su+bu))


# helper function to get the key out of a (key,value) pair
def first(L):
    return L[0]
