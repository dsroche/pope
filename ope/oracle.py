#!/usr/bin/env python3

"""
The class Oracle is provided which acts as a comparison oracle for
mutable OPE schemes.

Authored 2015 by Daniel S. Roche; US Government work in the public domain.
"""

import bisect

def identity(x):
    """Convienient definition of the identity function."""
    return x

class Oracle:
    """Accessed by an OPE back-end server in order to determine the order
    of elements.

    Also includes bookkeeping information on communication sizes.
    """

    def __init__(self, crypt, size):
        """Create a new comparison oracle.

        crypt is the encryption algorithm which should provide encode()
        and decode() functions.

        size is the maximum size of local (non-streaming) storage.
        """
        self.crypt = crypt
        self._data_in = 0
        self._data_out = 0
        self._rounds = 0
        self._tsize = size

    @property
    def max_size(self):
        """The maximum local (temporary) storage size."""
        return self._tsize

    def sort(self, L, lkey=identity, tiebreak=identity):
        """Sorts the given list of ciphertexts and returns the sorted list.
        lkey is the function to turn a list element into a ciphertext,
        for decrypting and then comparison (primary comparison).
        tiebreak is used to break ties; it does NOT involve any decryption."""
        res = sorted(L,
            key=lambda x: (self.crypt.decode(lkey(x)), tiebreak(x)))
        self._data_in += len(res)
        self._data_out += len(res)
        self._rounds += 1
        assert len(res) <= self.max_size
        return res

    def partition(self, needles, haystack, nkey=identity, haykey=identity):
        """Returns the index where each needle would be inserted in the
        given haystack to maintain sorted plaintext order.

        Note the haystack must already be sorted by plaintext order.
        An iteration over (needle, index) pairs is returned, where
        each index satisfies 0 <= i <= len(haystack), and
        haystack[i-1] < needle <= haystack[i],
        similar to the bisect.bisect_left command.

        If nkey or haykey or given, they are key functions to extract the
        comparison ciphertext from the given objects.
        """
        self._data_in += len(haystack)
        self._rounds += 1
        assert len(haystack) <= self.max_size
        # check the haystack is actually sorted
        sdhay = sorted(self.crypt.decode(haykey(x)) for x in haystack)
        assert all(sdhay[i] <= sdhay[i+1]
            for i in range(len(haystack)-1))
        for needle in needles:
            self._data_in += 1
            self._data_out += 1
            dk = self.crypt.decode(nkey(needle))
            yield (needle, bisect.bisect_left(sdhay, dk))

    def partition_sort(self, needles, haystack, nkey=identity, haykey=identity):
        """First sorts the haystack, then performs partition on that
        sorted list.

        Returns the sorted haystack, and then the result of partition.
        """
        shay = sorted(haystack,
            key=lambda x: (self.crypt.decode(haykey(x))))
        self._data_out += len(shay)
        return shay, self.partition(needles, shay, nkey, haykey)

    def find(self, needles, haystack, nkey=identity, haykey=identity):
        """Searches the given haystack for each thing in needles.

        Returned is a iteration of (needle, index) pairs, where 
        a negative index indicates the needle was not found.
        """
        self._data_in += len(haystack)
        self._rounds += 1
        assert len(haystack) <= self.max_size
        sdhay = sorted((self.crypt.decode(haykey(x)), ind)
            for (ind,x) in enumerate(haystack))
        for needle in needles:
            self._data_in += 1
            self._data_out += 1
            dk = self.crypt.decode(nkey(needle))
            found = bisect.bisect_left(sdhay, (dk, 0))
            if found < len(sdhay) and sdhay[found][0] == dk:
                yield (needle, sdhay[found][1])
            else:
                yield (needle, -1 - found)

    def find_sort(self, needles, haystack, nkey=identity, haykey=identity):
        """First sorts the haystack, then performs find on that sorted list.
        Returns the sorted haystack, and then the result of find.
        """
        shay = sorted(haystack,
            key=lambda x: (self.crypt.decode(haykey(x))))
        self._data_out += len(shay)
        return shay, self.find(needles, shay, nkey, haykey)

    def comm_in(self, reset=False):
        """Returns the total communication size so far."""
        res = self._data_in
        if reset:
            self._data_in = 0
        return res
    
    def comm_out(self, reset=False):
        res = self._data_out
        if reset:
            self._data_out = 0
        return res

    def comm_rounds(self, reset=False):
        """Returns the number of rounds of communication so far."""
        res = self._rounds
        if reset:
            self._rounds = 0
        return res

    def counts(self, reset=False):
        """Returns (data_in, data_out, rounds, max_size)."""
        return [
            self.comm_in(reset),
            self.comm_out(reset),
            self.comm_rounds(reset),
            self.max_size,
        ]

    def counts_summary(self, reset=False):
        """Prints counts data nicely."""
        ci, co, cr, ms = self.counts(reset)
        print("Over {} rounds, transferred {} to Cmp and {} from Cmp. Max size {}."
            .format(cr,ci,co,ms))


