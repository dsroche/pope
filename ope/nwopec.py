#!/usr/bin/env python3

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
import argparse

from ope import pope
from ope import nworacle

"""Single byte op-codes"""
CLEAR = b'c'
INSERT = b'i'
LOOKUP = b'l'
RANGE_SEARCH = b'r'
SIZE = b's'
TRAVERSE = b't'

DEBUG = True

class NwOpeClient:
    """Same functionality as opec.OpeClient, except only works with POPE and
    does it over a network."""

    def __init__(self, hostname, port, crypt, clearit=True):
        """hostname and port are for the POPE server.

        The given encryption algorithm crypt must support encode() and
        decode() methods, and must match the comparison oracle that the
        OPE server relies on.
        """
        self._addr = (hostname, port)
        self._crypt = crypt
        self._needs_clear = clearit
        self._conn = None

    def open(self):
        """opens the connection and allows operations"""
        if self._conn:
            raise RuntimeError("already open")
        self._conn = socket.create_connection(self._addr)
        self._sockfile = self._conn.makefile('rwb')

        if self._needs_clear:
            self._sockfile.write(CLEAR)
            self._sockfile.flush()
            self._needs_clear = False

    def __enter__(self):
        self.open()
        return self

    def close(self):
        """closes the connection"""
        if not self._conn:
            raise RuntimeError("not open; can't close it")
        try:
            self._sockfile.flush()
            self._sockfile.close()
            self._conn.close()
        except:
            pass
        del self._sockfile
        del self._conn
        self._conn = None

    def __exit__(self, t,v,r):
        self.close()

    def insert(self, key, value):
        # send opcode
        self._sockfile.write(INSERT)

        # send key and value
        pickle.dump(self._crypt.encode(key), self._sockfile)
        pickle.dump(self._crypt.encode(value), self._sockfile)

        self._sockfile.flush()

    def lookup(self, key):
        # send opcode
        self._sockfile.write(LOOKUP)

        # send key
        pickle.dump(self._crypt.encode(key), self._sockfile)
        self._sockfile.flush()

        # receive result
        encval = pickle.load(self._sockfile)

        self._sockfile.flush()

        if encval is None:
            return None
        else:
            return self._crypt.decode(encval)

    def stream_until_none(self):
        while True:
            obj = pickle.load(self._sockfile)
            if obj is None:
                break
            yield obj
        self._sockfile.flush()

    def range_search(self, key1, key2):
        if key2 < key1:
            return
        # send opcode
        self._sockfile.write(RANGE_SEARCH)

        # send keys
        pickle.dump(self._crypt.encode(key1), self._sockfile)
        pickle.dump(self._crypt.encode(key2), self._sockfile)
        self._sockfile.flush()

        res = [(self._crypt.decode(enkey), self._crypt.decode(enval))
                for enkey, enval in self.stream_until_none()]

        self._sockfile.flush()
        
        return res

    def size(self):
        # send opcode
        self._sockfile.write(SIZE)
        self._sockfile.flush()

        res = pickle.load(self._sockfile)
        self._sockfile.flush()
        return res

    def traverse(self):
        # send opcode
        self._sockfile.write(TRAVERSE)
        self._sockfile.flush()

        res = [(self._crypt.decode(enkey), self._crypt.decode(enval))
                for enkey, enval in self.stream_until_none()]
        
        self._sockfile.flush()
        
        return res

class PopeHandler(socketserver.BaseRequestHandler):
    # Note: must have field "serv" added to point to the underlying Pope instance

    def handle(self):
        with self.request.makefile('rwb') as sockfile:
            if DEBUG: print("Connection open")
            while True:
                # receive opcode
                opcode = sockfile.read(1)
                if not opcode:
                    if DEBUG: print("Connection closed")
                    return
                elif opcode == CLEAR:
                    if DEBUG: print("Received CLEAR request")
                    self.serv.clear()
                elif opcode == INSERT:
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
