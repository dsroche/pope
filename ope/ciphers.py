##################################################################
# This file is part of the POPE implementation.                  #
# Paper at https://eprint.iacr.org/2015/1106                     #
# U.S. Government work product, in the public domain.            #
# Written in 2015 by Daniel S. Roche, roche@usna.edu             #
##################################################################

"""
Ciphers for use with an OPE oracle.
"""

import Crypto.Hash.MD5
import Crypto.Cipher.AES
import Crypto.Random

class DumbCipher:
    """This dumb cipher just appends the key to the end of the ciphertext."""

    def __init__(self, key):
        self.key = "DumbKey" if key is None else key

    def encode(self, s):
        return str(s)[::-1] + '|' + self.key

    def decode(self, s):
        if s.endswith('|'+self.key):
            return s[-len(self.key)-2::-1]
        else:
            raise ValueError("wrong decryption key for {}: {}".format(s, self.key))

class AES:
    """A wrapper for PyCrypto's AES128 cipher."""

    def __init__(self, key=None):
        self.key = key
        r = Crypto.Random.new()
        if self.key:
            h = Crypto.Hash.MD5.new()
            h.update(self.key)
            self.realkey = h.digest()
        else:
            self.realkey = r.read(16)
        self.IV = r.read(16)
        self.ciph = Crypto.Cipher.AES.new(
                self.realkey, Crypto.Cipher.AES.MODE_ECB, self.IV)

    def encode(self, s):
        b = s.encode('utf8')
        assert not b.endswith(b'\0')
        rem = len(b) % 16
        if rem:
            b += b'\0' * (16 - rem)
        return self.ciph.encrypt(b)

    def decode(self, b):
        return self.ciph.decrypt(b).rstrip(b'\0').decode()


