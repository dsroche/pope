##################################################################
# This file is part of the POPE implementation.                  #
# Paper at https://eprint.iacr.org/2015/1106                     #
# U.S. Government work product, in the public domain.            #
# Written in 2015 by Daniel S. Roche, roche@usna.edu             #
##################################################################

"""
This file contains client and server classes for the backend POPE
server to connect to a comparison oracle.
"""

import socket
import socketserver
import pickle

"""Single byte op-codes"""
PARTITION = b'p'
PARTITION_SORT = b's'
FIND = b'f'
MAX_SIZE = b'm'

DEBUG = True

# convenience method
def identity(x):
    return x

class OracleClient:
    """Accessed by an OPE back-end server in order to determine the order
    of elements.
    """

    def __init__(self, hostname, port):
        """There should be an oracle server running on the specified hostname
        and port."""
        self._addr = (hostname, port)

        # go get the max size
        with socket.create_connection(self._addr) as conn:
            with conn.makefile('rwb') as sockfile:
                # send opcode
                sockfile.write(MAX_SIZE)
                sockfile.flush()

                self._max_size = pickle.load(sockfile)

    @property
    def max_size(self):
        return self._max_size

    def partition(self, needles, haystack, nkey=identity, haykey=identity):
        """Just like partition() in oracle.Oracle."""
        with socket.create_connection(self._addr) as conn:
            with conn.makefile('rwb') as sockfile:
                # send opcode
                sockfile.write(PARTITION)

                # send haystack and haykey
                pickle.dump(haystack, sockfile)
                pickle.dump(haykey, sockfile)

                # do partition
                res = self._do_partition(needles, nkey, sockfile)

        return res

    def partition_sort(self, needles, haystack, nkey=identity, haykey=identity):
        """Just like partition_sort() in oracle.Oracle."""
        with socket.create_connection(self._addr) as conn:
            with conn.makefile('rwb') as sockfile:
                # send opcode
                sockfile.write(PARTITION_SORT)

                # send haystack and haykey
                pickle.dump(haystack, sockfile)
                pickle.dump(haykey, sockfile)
                sockfile.flush()

                # receive sorted haystack
                shay = pickle.load(sockfile)

                # do the partition
                res = self._do_partition(needles, nkey, sockfile)

        return shay, res

    def _do_partition(self, needles, nkey, sockfile):
        """Convenience method for partition() and partition_sort()"""
        # send nkey
        pickle.dump(nkey, sockfile)

        # stream needles
        count = 0
        for needle in needles:
            pickle.dump(needle, sockfile)
            count += 1

        # indicate end
        pickle.dump(None, sockfile)
        sockfile.flush()

        # receive results
        res = [pickle.load(sockfile) for _ in range(count)]
        
        return res

    def find(self, needles, haystack, nkey=identity, haykey=identity):
        """Just like find() in oracle.Oracle."""
        with socket.create_connection(self._addr) as conn:
            with conn.makefile('rwb') as sockfile:
                # send opcode
                sockfile.write(FIND)

                # send haystack and haykey
                pickle.dump(haystack, sockfile)
                pickle.dump(haykey, sockfile)

                # send nkey
                pickle.dump(nkey, sockfile)

                # stream needles
                count = 0
                for needle in needles:
                    pickle.dump(needle, sockfile)
                    count += 1

                # indicate end
                pickle.dump(None, sockfile)
                sockfile.flush()

                # receive results
                res = [pickle.load(sockfile) for _ in range(count)]

        return res

class OracleHandler(socketserver.BaseRequestHandler):
    # Note: must have field "orc" added to point to the underlying Oracle instance

    def handle(self):
        with self.request.makefile('rwb') as sockfile:
            # receive opcode
            opcode = sockfile.read(1)

            if opcode == PARTITION:
                if DEBUG: print("Received PARTITION request")
                self.partition(sockfile)
            elif opcode == PARTITION_SORT:
                if DEBUG: print("Received PARTITION_SORT request")
                self.partition_sort(sockfile)
            elif opcode == FIND:
                if DEBUG: print("Received FIND request")
                self.find(sockfile)
            elif opcode == MAX_SIZE:
                if DEBUG: print("Received MAX_SIZE request")
                pickle.dump(self.orc.max_size, sockfile)
                sockfile.flush()
            else:
                raise RuntimeError("ORACLE ERROR: invalid opcode", opcode)
            if DEBUG:
                print("(finished request)")
                print()

    def stream_until_none(self, sockfile):
        while True:
            obj = pickle.load(sockfile)
            if obj is None:
                break
            yield obj

    def partition(self, sockfile):
        # read haystack and haykey
        haystack = pickle.load(sockfile)
        haykey = pickle.load(sockfile)

        # read nkey
        nkey = pickle.load(sockfile)

        # read needles
        needles = self.stream_until_none(sockfile)

        # stream back results
        for res in self.orc.partition(needles, haystack, nkey, haykey):
            pickle.dump(res, sockfile)

        sockfile.flush()

    def partition_sort(self, sockfile):
        # read haystack and haykey
        haystack = pickle.load(sockfile)
        haykey = pickle.load(sockfile)

        # sort haystack and send it back
        shay = self.orc.sort(haystack, haykey)
        pickle.dump(shay, sockfile)
        sockfile.flush()

        # read nkey
        nkey = pickle.load(sockfile)

        # read needles
        needles = self.stream_until_none(sockfile)

        # stream back results
        for res in self.orc.partition(needles, shay, nkey, haykey):
            pickle.dump(res, sockfile)

        sockfile.flush()

    def find(self, sockfile):
        # read haystack and haykey
        haystack = pickle.load(sockfile)
        haykey = pickle.load(sockfile)

        # read nkey
        nkey = pickle.load(sockfile)

        # read needles
        needles = self.stream_until_none(sockfile)

        # stream back results
        for res in self.orc.find(needles, haystack, nkey, haykey):
            pickle.dump(res, sockfile)

        sockfile.flush()

def get_oracle_server(the_oracle, hostname, port):
    """Creates a socketserver to relay requests to given oracle."""
    class Handler(OracleHandler):
        orc = the_oracle
    return socketserver.TCPServer((hostname, port), Handler)
