# POPE

Implementation of "Partial Order Preserving Encryption"
by Roche, Apon, Choi, and Yerukhimovich (2015); preprint available at
<https://eprint.iacr.org/2015/1106>.

This is currently a *proof-of-concept implementation* in Python that is
mostly meant to measure, validate, and test the communication costs.
For example, while the intention is to run the protocol over a network,
the current implementation involves only interaction between classes,
not using any actual network communication.

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

        **Note**: If someone wanted to make an actual client/server
        network version of POPE, this would be the place to do the
        network communication!

    +   `oracle.py`: A comparison oracle for order-preserving encoding.
        The role of the oracle is basically to receive ciphertexts and
        return their plaintext order (and nothing more).

    +   `pope.py`: The server-side implementation of the POPE scheme,
        including the buffer-tree-like data structure. Supports
        insertion and range queries, using a given comparison oracle to
        do the ordering.

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

*   `test`: Some programs to check the various OPE implementations.    

    +   `demo.py`: Inserts a few strings and performs a few range queries,
        in order to demonstrate how to use an OPE implementation.
