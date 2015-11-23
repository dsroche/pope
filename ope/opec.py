##################################################################
# This file is part of the POPE implementation.                  #
# Paper at https://eprint.iacr.org/2015/1106                     #
# U.S. Government work product, in the public domain.            #
# Written in 2015 by Daniel S. Roche, roche@usna.edu             #
##################################################################

"""
The OpeClient class is the client's view of an OPE key/value
store.
"""

from ope import ciphers
from ope import oracle
from ope import pope

def create_ope_client(ServerClass=pope.Pope, 
        Cipher=ciphers.AES, key=None, local_size=100):
    """Creates a new cipher instance with specified key, a new comparison
    oracle using that cipoher, then a new OPE server implementation using
    that oracle, and finally returns a new OpeClient connected to that
    server."""

    ciph = Cipher(key)
    orc = oracle.Oracle(ciph, local_size)
    serv = ServerClass(orc)
    return OpeClient(serv, ciph)


class OpeClient:
    """Able to access a remote key/value store with encrypted keys
    and values."""

    def __init__(self, server, crypt):
        """Creates a new client view of the given OPE key/value server.
        
        The given encryption algorithm crypt must support encode() and
        decode() methods, and must match the comparison oracle that the
        OPE server relies on.
        """
        
        self._serv = server
        self._crypt = crypt


    def insert(self, key, value):
        self._serv.insert(self._crypt.encode(key), self._crypt.encode(value))

    def lookup(self, key):
        encval = self._serv.lookup(self._crypt.encode(key))
        if encval is None:
            return None
        else:
            return self._crypt.decode(encval)

    def range_search(self, key1, key2):
        if key1 <= key2:
            for enkey, enval in self._serv.range_search(self._crypt.encode(key1), self._crypt.encode(key2)):
                yield (self._crypt.decode(enkey), self._crypt.decode(enval))

    def size(self):
        return self._serv.size()

    def traverse(self):
        for (k,v) in self._serv.traverse():
            yield self._crypt.decode(k), self._crypt.decode(v)

