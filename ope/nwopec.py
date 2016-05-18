##################################################################
# This file is part of the POPE implementation.                  #
# Paper at https://eprint.iacr.org/2015/1106                     #
# U.S. Government work product, in the public domain.            #
# Written in 2015 by Daniel S. Roche, roche@usna.edu             #
##################################################################

"""
This file contains client and server classes for the front-end
client and POPE server interface.
"""

import socket
import socketserver
import pickle

"""Single byte op-codes"""
INSERT = b'i'
LOOKUP = b'l'
RANGE_SEARCH = b'r'
SIZE = b's'
TRAVERSE = b't'

DEBUG = True

class NwOpeClient:
    """Same functionality as opec.OpeClient, except only works with POPE and
    does it over a network."""

    def __init__(self, hostname, port, crypt):
        """hostname and port are for the POPE server.

        The given encryption algorithm crypt must support encode() and
        decode() methods, and must match the comparison oracle that the
        OPE server relies on.
        """
        self._addr = (hostname, port)
        self._crypt = crypt

    def insert(self, key, value):
        with socket.create_connection(self._addr) as conn:
            with conn.makefile('rwb') as sockfile:
                # send opcode
                sockfile.write(INSERT)

                # send key and value
                pickle.dump(self._crypt.encode(key), sockfile)
                pickle.dump(self._crypt.encode(value), sockfile)

                sockfile.flush()

    def lookup(self, key):
        with socket.create_connection(self._addr) as conn:
            with conn.makefile('rwb') as sockfile:
                # send opcode
                sockfile.write(LOOKUP)

                # send key
                pickle.dump(self._crypt.encode(key), sockfile)
                sockfile.flush()

                # receive result
                encval = pickle.load(sockfile)

        if encval is None:
            return None
        else:
            return self._crypt.decode(encval)

    def stream_until_none(self, sockfile):
        while True:
            obj = pickle.load(sockfile)
            if obj is None:
                break
            yield obj

    def range_search(self, key1, key2):
        if key2 < key1:
            return
        with socket.create_connection(self._addr) as conn:
            with conn.makefile('rwb') as sockfile:
                # send opcode
                sockfile.write(RANGE_SEARCH)

                # send keys
                pickle.dump(self._crypt.encode(key1), sockfile)
                pickle.dump(self._crypt.encode(key2), sockfile)
                sockfile.flush()

                res = [(self._crypt.decode(enkey), self._crypt.decode(enval))
                        for enkey, enval in self.stream_until_none(sockfile)]
        
        return res

    def size(self):
        with socket.create_connection(self._addr) as conn:
            with conn.makefile('rwb') as sockfile:
                # send opcode
                sockfile.write(SIZE)
                sockfile.flush()

                return pickle.load(sockfile)

    def traverse(self):
        with socket.create_connection(self._addr) as conn:
            with conn.makefile('rwb') as sockfile:
                # send opcode
                sockfile.write(TRAVERSE)
                sockfile.flush()

                res = [(self._crypt.decode(enkey), self._crypt.decode(enval))
                        for enkey, enval in self.stream_until_none(sockfile)]
        
        return res

class PopeHandler(socketserver.BaseRequestHandler):
    # Note: must have field "serv" added to point to the underlying Pope instance

    def handle(self):
        with self.request.makefile('rwb') as sockfile:
            # receive opcode
            opcode = sockfile.read(1)

            if opcode == INSERT:
                if DEBUG: print("Received INSERT request")
                self.insert(sockfile)
            elif opcode == LOOKUP:
                if DEBUG: print("Received LOOKUP request")
                self.lookup(sockfile)
            elif opcode == RANGE_SEARCH:
                if DEBUG: print("Received RANGE_SEARCH request")
                self.range_search(sockfile)
            elif opcode == TRAVERSE:
                if DEBUG: print("Received TRAVERSE request")
                self.traverse(sockfile)
            elif opcode == SIZE:
                if DEBUG: print("Received SIZE request")
                pickle.dump(self.serv.size(), sockfile)
                sockfile.flush()
            else:
                raise RuntimeError("POPE SERVER ERROR: invalid opcode", opcode)
            if DEBUG:
                print("(finished request)")
                print()
    
    def insert(self, sockfile):
        # get key and value
        key = pickle.load(sockfile)
        value = pickle.load(sockfile)

        # do it
        self.serv.insert(key, value)

    def lookup(self, sockfile):
        # get key
        key = pickle.load(sockfile)

        # get result
        res = self.serv.lookup(key)

        # return result
        pickle.dump(res, sockfile)
        sockfile.flush()

    def range_search(self, sockfile):
        # get keys
        key1 = pickle.load(sockfile)
        key2 = pickle.load(sockfile)

        # get result
        res = self.serv.range_search(key1, key2)

        # send back results
        self.send_all(sockfile, res)

    def traverse(self, sockfile):
        # get result
        res = self.serv.traverse()

        # send back results
        self.send_all(sockfile, res)

    def send_all(self, sockfile, L):
        for x in L:
            pickle.dump(x, sockfile)
        pickle.dump(None, sockfile)
        sockfile.flush()


def get_pope_server(the_pope, hostname, port):
    """Creates a socketserver to relay requests to given POPE instance."""
    class Handler(PopeHandler):
        serv = the_pope
    return socketserver.TCPServer((hostname, port), Handler)
