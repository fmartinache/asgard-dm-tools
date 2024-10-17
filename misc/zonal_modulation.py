#!/usr/bin/env python3
from xaosim.shmlib import shm
import numpy as np
import time

channel = 3  # dm channel to address
dmc = shm(f'/dev/shm/dm1disp{channel:02d}.im.shm')
nel = dmc.mtdata['nel']
sz = dmc.mtdata['size'][1]
a0 = 0.3
dt = 0.2

for ii in range(nel):
    dmmap = np.zeros((sz, sz))
    dmmap[ii % sz, ii // sz] = a0
    time.sleep(dt)
    dmc.set_data(dmmap)

dmc.set_data(np.zeros((sz, sz)))
