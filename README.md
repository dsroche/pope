# POPE

Implementation of "Partial Order Preserving Encryption"
by Roche, Apon, Choi, and Yerukhimovich (2016)
from ACM CCS 2016; preprint available at
<https://arxiv.org/abs/1610.04025> or
<https://eprint.iacr.org/2015/1106>.

This is currently a *proof-of-concept implementation* in Python that is
mostly meant to measure, validate, and test the communication costs.

## System requirements

Tested using Python 3.2.3 and later. It's possible that earlier
versions of Python 3 will work as well, but not tested.

Requires the pycrypto library, available from
<https://github.com/dlitz/pycrypto>.

## Directory structure

*   `ope`: Contains our implementations of client/server based
    order-preserving encoding schemes, including the POPE scheme itself.

    +   `opec.py`: An OPE client, which glues together the server
        back-end (mOPE or POPE, for example) with the comparison oracle,
        and provides a convenient front-end interface for insertions and
        range queries.

        **Note**: This is just for testing purposes, as everything is
        running in memory within the same Python instance, not actually
        over a network link.

    +   `nwopec.py`: An OPE client that can access a POPE server over
        the network. Similar functionality to the `opec` module in
        giving a convenient client front-end to a POPE back-end, but
        actually uses sockets to communicate (potentially) over the
        network.

    +   `oracle.py`: A comparison oracle for order-preserving encoding.
        The role of the oracle is basically to receive ciphertexts and
        return their plaintext order (and nothing more).

        **Note**: This version is for testing purposes only, and does
        not work over a network.

    +   `nworacle.py`: Similar functionality to the `oracle` module, but
        in a client/server setup to use socket-based network
        communication.

    +   `pope.py`: The server-side implementation of the POPE scheme,
        including the buffer-tree-like data structure. Supports
        insertion and range queries, using a given comparison oracle to
        do the ordering. The comparison oracle can be `oracle.Oracle` if
        running locally, or `nworacle.OracleClient` over a network
        socket.

    +   `mope.py`: Our implementation of the mOPE scheme of Popa, Li,
        and Zeldovich from <https://eprint.iacr.org/2013/129>.
        The implementation is not highly-tuned, but is comparable to our
        POPE implementation, and in the same model, in order to attempt
        a fair comparison.

    +   `cheater.py`: A "fake" OPE implementation that cheats by simply
        retrieving the decryption key from the comparison oracle and
        does everything in plaintext. Used for testing and debugging
        purposes only, of course.

    +   `ciphers.py`: Common wrapper classes for symmetric ciphers.
        Included are a dummy cipher used for debugging, and a wrapper of
        PyCrypto's AES128 implementation.

+   `servers`: Servers to host OPE backends and comparison oracles over
    a network socket

    +   `orac_serv.py`: Hosts a comparison oracle server on a desired
        port. This comparison oracle needs to know the client's
        decryption key, and listens for comparison requests from a
        connecting POPE or MOPE instance.

    +   `pope_serv.py`: Hosts a POPE server on a desired port.
        This server does *not* have the client's decryption key, but
        needs to know how to access a comparison oracle.

    +   `mope_serv.py`: Similar to the `pope_serv` module, but wraps our
        implementation of the mutable OPE scheme from Popa, Li, and
        Zeldovich (IEEE S&P 2013).

*   `test`: Some programs to check the various OPE implementations.

    +   `demo.py`: Inserts a few strings and performs a few range queries,
        in order to demonstrate how to use an OPE implementation.

    +   `check.py`: Inserts 1000 or so random entries into all available
        OPE implementations and performs random range queries, checking
        all of the results for correctness.

    +   `incomparable.py`: Experimentally measures the number of
        incomparable elements after inserting California salary database
        entries and performing random range queries.

        **Note**: requires [Python Imaging
        Library](http://www.pythonware.com/products/pil/)

    +   `nwbench.py`: Test code to benchmark the networked POPE
        implementation using California salary data

    +   `nwrun.sh`: Script to start up the servers and run the `nwbench`
        test.

    +   `nwbench-or.py`: Similar to `nwbench`, but only runs the
        comparison oracle over the network and not the POPE server.

    +   `nwrun-or.sh`: Script to start up the servers and run the `nwbench-or`
        test.

    +   `nwspeed.sh`: Used by the `nwrun.sh` and `nwrun-or.sh` scripts
        to throttle network speed using iptables,
        [and Linux traffic
        control](http://www.lartc.org/manpages/tc.txt).

    +   `progbar.py`: Displays a nice Unicode-based progress bar.
