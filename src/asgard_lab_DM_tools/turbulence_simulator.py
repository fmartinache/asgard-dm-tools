#!/usr/bin/env python3

import numpy as np
import time
import threading
import glob
import argparse

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
shm0_names = np.sort(glob.glob(f"/dev/shm/dm[1-{ndm}].*"))

if (len(shm_names) < ndm):
    print("DM server not running?")
    exit(0)

dmap = np.zeros((dms, dms))

shms = []  # the turbulence shm
shm0s = []  # the DM channel (so signal driver)


for ii in range(ndm):
    shms.append(shm(shm_names[ii]))
    shm0s.append(shm(shm0_names[ii], nosem=False))

gain = 0.1  # to be adjusted!
keepgoing = True
phase = atmo_screen(isz, ll, r0, L0, fc=2).real
opd = wl / (2 * np.pi) * np.tile(phase, (2, 2))

# =============================================================================
def __flow__(delay=0.1, dx=2, dy=1):
    yy, xx = 0, 0
    global dms, gain, keepgoing, opd

    while keepgoing:
        yy = (yy + dy) % isz
        xx = (xx + dx) % isz

        for kk in range(ndm):
            dmap = opd[yy0[kk]+yy:yy0[kk]+yy+dms, xx:xx+dms]
            # dmap -= dmap.mean()
            shms[kk].set_data(gain * dmap)
            shm0s[kk].post_sems(1)
        time.sleep(delay)


# =============================================================================
def main():
    global keepgoing, phase, opd
    delay = 0.1
    dx, dy = 2, 1


    parser = argparse.ArgumentParser(
        prog = 'turbulence_simulator',
        description = 'A command line simulator for Asgard',
        epilog = "Press enter to exit program")

    parser.add_argument('--r0', type=float, default=0.2,
                        help='The Fried parameter (in meters, default=0.2)')

    parser.add_argument('--tdiam', type=float, default=1.8,
                        help='Telescope diameter (in meters, default=1.8)')

    parser.add_argument('--corr', type=float, default=1.0,
                        help='Correction factor by upstream AO (default=1, no correction)')

    parser.print_help()

    args = parser.parse_args()
    print(args)
    r0 = float(args.r0)
    
    tdiam = float(args.tdiam)
    if tdiam < 2: # AT scenario
        fc = 2  # cut-off frequency of NAOMI
    else:
        fc = 20  # cut-off frequency of GPAO

    correc = float(args.corr)

    print(f"r0     = {r0:.2f} meters")
    print(f"Tdiam  = {tdiam:.2f} meters")
    print(f"Correc = {correc:.2f}")

    isz = dms * ntdiam
    ll = tdiam * ntdiam
    # L0 = 20.0    # turbulence outer scale
    wl = 1.6     # wavelength (in microns)

    phase = atmo_screen(isz, ll, r0, L0, correc=correc, fc=fc).real
    opd = wl / (2 * np.pi) * np.tile(phase, (2, 2))
    
    t = threading.Thread(target=__flow__, args=(delay, dx, dy))
    t.start()

    input("Press enter to stop")
    keepgoing = False
    dmap = np.zeros((dms, dms))
    for kk in range(ndm):
        shms[kk].set_data(dmap)
        shm0s[kk].post_sems(1)                

# =============================================================================
if __name__ == "__main__":
    main()
