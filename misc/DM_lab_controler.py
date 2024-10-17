#!/usr/bin/env python3

from xaosim.QtMain import QtMain
from xaosim.shmlib import shm
import numpy as np
import matplotlib.cm as cm

from PyQt5 import QtCore, QtGui, uic
from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QLabel, QMainWindow
from PyQt5.QtGui import QImage

import pyqtgraph as pg
import sys
import os

# =====================================================================
# =====================================================================
home = os.getenv('HOME')
myqt = 0  # myqt is a global variable


def main():
    global myqt
    myqt = QtMain()
    gui = MyWindow()
    myqt.mainloop()
    myqt.gui_quit()
    sys.exit()


# =====================================================================
#                               Tools
# =====================================================================
def arr2im(arr, vmin=False, vmax=False, pwr=1.0, cmap=None, gamma=1.0):
    ''' ------------------------------------------
    convert numpy array into image for display

    limits dynamic range, power coefficient and
    applies colormap
    ------------------------------------------ '''
    arr2 = arr.astype('float')
    if vmin is False:
        mmin = arr2.min()
    else:
        mmin = vmin

    if vmax is False:
        mmax = arr2.max()
    else:
        mmax = vmax

    arr2 -= mmin
    if mmax != mmin:
        arr2 /= (mmax-mmin)

    arr2 = arr2**pwr

    if cmap is None:
        mycmap = cm.jet
    else:
        mycmap = cmap

    res = mycmap(arr2)
    res[:, :, 3] = gamma
    return(res)


# =====================================================================
#                        Main GUI object
# =====================================================================
class MyWindow(QMainWindow):
    def __init__(self):
        self.mySHM = None  # handle for mmapped SHM file
        self.vmin = False
        self.vmax = False
        self.pwr = 1.0
        self.mycmap = cm.jet

        super(MyWindow, self).__init__()
        uic.loadUi('./DM_lab_controler.ui', self)

        # ==============================================
        self.show()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.refresh_all)
        self.timer.start(100)

    # =========================================================
    def refresh_all(self):
        pass

    # =========================================================
    def closeEvent(self, event):
        sys.exit()


# ==========================================================
# ==========================================================
if __name__ == "__main__":
    main()
