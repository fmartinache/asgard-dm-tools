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

skullmap = np.zeros((sz, sz))

skullmap[4:12, 2:9] = a0
skullmap[9:11, 3:5] = 0.0  # eye
skullmap[9:11, 6:8] = 0.0  # eye
skullmap[6:8, 5] = 0.0     # nose
# skullmap[6, 4:7] = 0.0     # nose

skullmap[4, 2] = 0.0    # tooth
skullmap[4, 4] = 0.0    # tooth
skullmap[4, 6] = 0.0    # tooth
skullmap[4, 8] = 0.0    # tooth

skullmap[6:10, 1] = a0  # ear
skullmap[6:10, 9] = a0  # ear

dmc.set_data(skullmap)

jawmap = np.zeros((sz, sz))

jawmap[0:3, 3:8] = a0
jawmap[2, 3] = 0.0
jawmap[2, 5] = 0.0
jawmap[2, 7] = 0.0

# sequence

dmc.set_data(skullmap + np.roll(jawmap, 1, axis=0))
time.sleep(dt * 6)

dmc.set_data(skullmap + np.roll(jawmap, 0, axis=0))
time.sleep(dt)

dmc.set_data(skullmap + np.roll(jawmap, 1, axis=0))
time.sleep(dt * 2)

dmc.set_data(skullmap + np.roll(jawmap, 0, axis=0))
time.sleep(dt)

dmc.set_data(skullmap + np.roll(jawmap, 1, axis=0))
time.sleep(dt * 2)

dmc.set_data(skullmap + np.roll(jawmap, 0, axis=0))
time.sleep(dt)

dmc.set_data(skullmap + np.roll(jawmap, 1, axis=0))
time.sleep(dt * 2)

dmc.set_data(skullmap + np.roll(jawmap, 0, axis=0))
time.sleep(dt)

dmc.set_data(skullmap + np.roll(jawmap, 1, axis=0))
time.sleep(dt * 2)

dmc.set_data(skullmap + np.roll(jawmap, 0, axis=0))
time.sleep(dt)

dmc.set_data(skullmap + np.roll(jawmap, 1, axis=0))
time.sleep(dt * 2)

dmc.set_data(skullmap + np.roll(jawmap, 0, axis=0))
time.sleep(dt * 6)

dmc.set_data(np.zeros((sz, sz)))
dmc.close(erase_file=False)
