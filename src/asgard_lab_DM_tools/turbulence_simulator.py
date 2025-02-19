#!/usr/bin/env python3

import numpy as np
import time
import threading
import glob

from xaosim.wavefront import atmo_screen
from xaosim.shmlib import shm

# =============================================================================
# script parameters

# should become arguments of the command line

ndm = 4      # number of DMs connected
chn = 3      # turbulence channel

tdiam = 1.8  # telescope diameter (in meters)
r0 = 0.2     # Fried parameter (in meters)
ntdiam = 10  #
dms = 12     # DM size (in actuators)

isz = dms * ntdiam
ll = tdiam * ntdiam
L0 = 20.0    # turbulence outer scale
wl = 1.6     # wavelength (in microns)

yy0 = np.arange(ndm) * (dms + 5)

shm_names = np.sort(glob.glob(f"/dev/shm/dm[1-{ndm}]disp{chn:02d}*"))

if (len(shm_names) < ndm):
    print("DM server not running?")
    exit(0)

dmap = np.zeros((dms, dms))

shms = []

phase = atmo_screen(isz, ll, r0, L0, fc=5).real
opd = wl / (2 * np.pi) * np.tile(phase, (2, 2))

for ii in range(ndm):
    shms.append(shm(shm_names[ii]))

gain = 0.1  # to be adjusted!
keepgoing = True

# =============================================================================
def __flow__(delay=0.1, dx=2, dy=1):
    yy, xx = 0, 0
    global phscreens, dms, gain, keepgoing

    while keepgoing:
        yy = (yy + dy) % isz
        xx = (xx + dx) % isz

        for kk in range(ndm):
            dmap = opd[yy0[kk]+yy:yy0[kk]+yy+dms, xx:xx+dms]
            dmap -= dmap.mean()
            shms[kk].set_data(gain * dmap)
        time.sleep(delay)


# =============================================================================
def main():
    global keepgoing
    delay = 0.1
    dx, dy = 2, 1

    t = threading.Thread(target=__flow__, args=(delay, dx, dy))
    t.start()

    input("Press enter to stop")
    keepgoing = False
    dmap = np.zeros((dms, dms))
    for kk in range(ndm):
        shms[kk].set_data(dmap)
    
# =============================================================================
if __name__ == "__main__":
    main()
