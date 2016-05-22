#!/usr/bin/env python3

##################################################################
# This file is part of the POPE implementation.                  #
# Paper at https://eprint.iacr.org/2015/1106                     #
# U.S. Government work product, in the public domain.            #
# Written in 2015 by Daniel S. Roche, roche@usna.edu             #
##################################################################

"""
An executable script to start up a POPE server
"""

import argparse

from ope import mope
from ope import nworacle
from ope import nwopec

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Start the POPE server')
    parser.add_argument('oracle_hostname')
    parser.add_argument('oracle_port', type=int)
    parser.add_argument('pope_hostname')
    parser.add_argument('pope_port', type=int)
    parser.add_argument('-d', '--debug', action='store_true', default=False)
    args = parser.parse_args()

    nwopec.DEBUG = args.debug

    with nworacle.OracleClient(args.oracle_hostname, args.oracle_port) as orc:
        popeinst = mope.Mope(orc)

        serv = nwopec.get_pope_server(popeinst, args.pope_hostname, args.pope_port)

        print("The mOPE server is listening on", args.pope_hostname, "port", args.pope_port)
        print("Press CTL-C to stop")

        try:
            serv.serve_forever()
        except KeyboardInterrupt:
            print("Goodbye!")
        finally:
            serv.shutdown()
            serv.server_close()
