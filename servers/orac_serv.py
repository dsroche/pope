#!/usr/bin/env python3

##################################################################
# This file is part of the POPE implementation.                  #
# Paper at https://eprint.iacr.org/2015/1106                     #
# U.S. Government work product, in the public domain.            #
# Written in 2015 by Daniel S. Roche, roche@usna.edu             #
##################################################################

"""
A simple script to start up a comparison oracle server
"""

import argparse

from ope import ciphers
from ope import oracle
from ope import nworacle

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start the Oracle server')
    parser.add_argument('oracle_hostname')
    parser.add_argument('oracle_port', type=int)
    parser.add_argument('passphrase')
    parser.add_argument('local_size', type=int)
    parser.add_argument('-d', '--debug', action='store_true', default=False)
    args = parser.parse_args()

    nworacle.DEBUG = args.debug

    crypt = ciphers.AES(args.passphrase)
    orc = oracle.Oracle(crypt, args.local_size)

    serv = nworacle.get_oracle_server(orc, args.oracle_hostname, args.oracle_port)

    print("The comparison oracle server is listening on", args.oracle_hostname, "port", args.oracle_port)
    print("Press CTL-C to stop")

    try:
        serv.serve_forever()
    except KeyboardInterrupt:
        print("Goodbye!")
    finally:
        serv.shutdown()
        serv.server_close()
