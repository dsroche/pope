#!/usr/bin/env python3

import math
import subprocess
import sys

class ProgressBar:
    def __init__(self, maxval=100, basic=False, dest=sys.stderr):
        self.maxval = maxval
        self.dest = dest
        self.val = 0
        self.redraw_at = 0
        self.partial = [' ']
        for code in range(0x258f, 0x2587, -1):
            self.partial.append(chr(code))
        self.gran = len(self.partial) - 1
        self.active = False
        self.basic = basic

    def start(self):
        assert not self.active
        print(file=self.dest)
        self.active = True
        self.redraw()

    def finish(self):
        assert self.active
        self.redraw()
        self.active = False
        print('\n', file=self.dest)

    def update(self, newval):
        assert self.val <= newval <= self.maxval
        self.val = newval
        if self.active and self.val >= self.redraw_at:
            self.redraw()

    def __iadd__(self, increment):
        self.update(self.val + increment)
        return self

    def __int__(self):
        return self.val

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, typ, val, cb):
        self.finish()
        return (typ is None)

    def redraw(self):
        if self.basic:
            percent = self.val * 100 // self.maxval
            print('\rProgress: {}%'.format(percent), end="", file=self.dest)
            self.redraw_at = max(self.val+1, ((percent+1)*self.maxval + 99) // 100)
        else:
            assert self.active
            total_width = int(subprocess.check_output(['stty', 'size']).split()[1])
            total_blocks = total_width - 6
            total_subblocks = total_blocks * self.gran
            assert 0 <= self.val <= self.maxval
            percent = self.val * 100 // self.maxval
            subblocks = self.val * total_subblocks // self.maxval
            nfull, remain = divmod(subblocks, self.gran)
            line = "\r\u2592"
            line += self.partial[-1] * nfull
            if remain:
                line += self.partial[remain]
                line += self.partial[0] * (total_blocks - nfull - 1)
            else:
                line += self.partial[0] * (total_blocks - nfull)
            line += "\u2592{:>3}%".format(percent)
            print(line, end="", file=self.dest)
            self.redraw_at = min(
                ((percent+1)*self.maxval + 99) // 100,
                ((subblocks+1)*self.maxval + total_subblocks-1) // total_subblocks
                )
            assert self.redraw_at > self.val

if __name__ == '__main__':
    import random
    import time
    maxval = 1234567
    maxup = 100000
    delay = .5
    with ProgressBar(maxval) as pbar:
        while True:
            if int(pbar) + maxup > maxval: break
            pbar += random.randrange(maxup)
            time.sleep(delay)
