#!/usr/bin/env python3

''' ---------------------------------------------------------------------------
My attempt to get a single GUI with tabs to drive the 4 DMs.
--------------------------------------------------------------------------- '''

from xaosim.QtMain import QtMain
from xaosim.shmlib import shm
from xaosim.zernike import mkzer1
from xaosim.zernike import zer_name_list as zer_names
from xaosim.pupil import F_test_figure as ftest
from xaosim.pupil import _dist as dist
from scipy.interpolate import griddata

import numpy as np
import matplotlib.cm as cm

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRect

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel


import pyqtgraph as pg

import sys
import os
import glob
import json
import argparse
import time

# =====================================================================
#                   global variables and tools
# =====================================================================
conf_dir = os.getenv('HOME') + "/.config/"

myqt = 0   # myqt is a global variable
ndm = 4    # the number of DMs to control
nzer = 11  # the number of Zernike modes to control
dms = 12   # the DM size
aps = 10   # the aperture grid size

gui_conf = {}  # dictionary to keep track of checkbox & sliders status

flat_cmd_files = [  # the factory flats
    "17DW019#113_FLAT_MAP_COMMANDS.txt",
    "17DW019#053_FLAT_MAP_COMMANDS.txt",
    "17DW019#093_FLAT_MAP_COMMANDS.txt",
    "17DW019#122_FLAT_MAP_COMMANDS.txt"]

# ----------------------------------------
dd = dist(dms, dms, between_pix=True)  # auxilliary array
tprad = 5.5  # the taper function radius
taper = np.exp(-(dd/tprad)**20)  # power to be adjusted ?
amask = taper > 0.4  # seems to work well
circ = dd < 4

font1 = QtGui.QFont()
font1.setPointSize(12)
font1.setBold(True)

font2 = QtGui.QFont()
font2.setPointSize(48)
font2.setBold(True)

# =====================================================================
#                               Tools
# =====================================================================
def arr2im(arr, vmin=False, vmax=False, pwr=1.0, cmap=None, gamma=1.0):
    ''' ------------------------------------------
    convert numpy array into image for display

    limits dynamic range, power coefficient and
    applies colormap
    ------------------------------------------ '''
    arr2 = arr.astype('float').T
    mmin = arr2.min() if vmin is False else vmin
    mmax = arr2.max() if vmax is False else vmax
    mycmap = cm.magma if cmap is None else cmap

    arr2 -= mmin
    if mmax != mmin:
        arr2 /= (mmax-mmin)
    arr2 = arr2**pwr

    res = mycmap(arr2)
    res[:, :, 3] = gamma
    return(res)


def cmd_2_map2D(cmd, fill=np.nan):
    '''Convert a 139 cmd into a 2D DM map for display.

    Just need to add the four corners (0 or nan) and reshape
    Parameters:
    - cmd  : 1D numpy array of 139 components
    - fill : filling values for corners (default = np.nan)
    '''
    return np.insert(cmd, [0, 10, 130, 140], fill).reshape((dms, dms))


def fill_mode(dmmap):
    ''' Extrapolate the modes outside the aperture to ensure edge continuity

    Parameter:
    ---------
    - a single 2D DM map
    '''
    out = True ^ amask  # outside the aperture
    gx, gy = np.mgrid[0:dms, 0:dms]
    points = np.array([gx[amask], gy[amask]]).T
    values = np.array(dmmap[amask])
    grid_z0 = griddata(points, values, (gx[out], gy[out]), method='nearest')
    res = dmmap.copy()
    res[out] = grid_z0
    return res


def zer_bank(i0, i1, extrapolate=True, tapered=False):
    ''' ------------------------------------------
    Returns a 3D array containing 2D (dms x dms)
    maps of Zernike modes for Noll index going
    from i0 to i1 included.

    Parameters:
    ----------
    - i0: the first Zernike index to be used
    - i1: the last Zernike index to be used
    - tapered: boolean (tapers the Zernike)
    ------------------------------------------ '''
    dZ = i1 - i0 + 1
    res = np.zeros((dZ, dms, dms))
    for ii in range(i0, i1+1):
        test = mkzer1(ii, dms, aps//2, limit=False)
        # if ii == 1:
        #     test *= circ
        if ii != 1:
            test -= test[amask].mean()
            test /= test[amask].std()
        if extrapolate is True:
            # if ii != 1:
            test = fill_mode(test)
        if tapered is True:
            test *= taper * mask
        res[ii-i0] = test

    return(res)

# ==========================================================
#              Creating the Application
# ==========================================================
class App(QtWidgets.QMainWindow): 
    # ------------------------------------------------------
    def __init__(self):
        super().__init__()
        self.title = 'Asgard MDM control Widget'
        self.left, self.top = 0, 0
        self.width, self.height = 820, 600

        self.setWindowTitle(self.title) 
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.setMinimumSize(QtCore.QSize(self.width, self.height))
        self.setMaximumSize(QtCore.QSize(self.width, self.height))
        self.tab_widget = MyMultiTabWidget(self) 
        self.setCentralWidget(self.tab_widget) 

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.refresh)
        self.timer.start(200)

    # ------------------------------------------------------
    def refresh(self):
        ii = self.tab_widget.qtab.currentIndex()
        if ii < ndm:
            self.tab_widget.tabs[ii].update_img()

    # ------------------------------------------------------
    def closeEvent(self, event):
        global gui_conf
        # must free shared memory structures
        self.tab_widget.close_shm()

        with open(f'{conf_dir}MDM_lab_GUI.json', 'w') as json_config:
            json.dump(gui_conf, json_config, indent=2)        
        sys.exit()

# ==========================================================
#         Handling the behavior of a DM tab
# ==========================================================
class DMTabWidget(QtWidgets.QWidget):
    def __init__(self, parent, dmid):
        global gui_conf
        super(QtWidgets.QWidget, self).__init__(parent)
        self.dmid = dmid

        self.nzer = nzer       # number of zernike modes to work with
        self.amax = 0.2      # max. modulation amplitude
        self.nzstep = 40     # number of steps for Zernike sliders

        self.data_img = np.zeros((dms, dms))

        # ==== the left-hand panel ====
        self.lbl_live = QtWidgets.QLabel(self)
        self.lbl_live.setText(f"DM #{self.dmid} - live status")
        self.lbl_live.setFont(font1)
        self.lbl_live.setAlignment(QtCore.Qt.AlignCenter)
        
        self.gView_shm = pg.PlotWidget(self)
        self.gView_shm.hideAxis('left')
        self.gView_shm.hideAxis('bottom')

        self.imv_data = pg.ImageItem()
        self.overlay = pg.GraphItem()
        self.gView_shm.addItem(self.imv_data)
        
        self.lbl_dmid = QtWidgets.QLabel(self)
        self.lbl_dmid.setText(f"DM #{self.dmid}")
        self.lbl_dmid.setFont(font2)
        self.lbl_dmid.setAlignment(QtCore.Qt.AlignCenter)

        self.pB_reset = QtWidgets.QPushButton(self)
        # self.pB_reset.setToolTip("Reset the DM to neutral state")
        self.pB_reset.setText("RESET")

        # ==== the right-hand panel ====
        self.lbl_ctrl = QtWidgets.QLabel(self)
        self.lbl_ctrl.setText("DM control tools")
        self.lbl_ctrl.setFont(font1)
        self.lbl_ctrl.setAlignment(QtCore.Qt.AlignCenter)
        
        self.chB_actv_flat = QtWidgets.QCheckBox(self)
        self.chB_actv_flat.setText("Flat")
        self.chB_actv_flat.setChecked(
            gui_conf[f'dm{self.dmid}']['flat_chbox'])

        # --------------------- CROSS -----------------
        # activation checkbox for CROSS
        self.chB_actv_cross = QtWidgets.QCheckBox(self)
        self.chB_actv_cross.setText("Cross")
        self.chB_actv_cross.setChecked(
            gui_conf[f'dm{self.dmid}']['cross_chbox'])

        # slider for CROSS amplitude
        self.slid_cross = QtWidgets.QSlider(self)
        self.slid_cross.setOrientation(QtCore.Qt.Horizontal)
        self.slid_cross.setRange(-self.nzstep, self.nzstep)
        self.slid_cross.setValue(gui_conf[f'dm{self.dmid}']['cross_a0'])
        self.cross_a0 = self.slid_cross.value() * self.amax / self.nzstep

        # CROSS amplitude display label
        self.lbl_disp_cross = QtWidgets.QLabel(self)
        self.lbl_disp_cross.setText(f"{self.cross_a0:0.3f}")

        # --------------------- FTEST -----------------
        # activation checkbox for FTEST
        self.chB_actv_ftest = QtWidgets.QCheckBox(self)
        self.chB_actv_ftest.setText("F-test")
        self.chB_actv_ftest.setChecked(
            gui_conf[f'dm{self.dmid}']['ftest_chbox'])

        # slider for FTEST amplitude
        self.slid_ftest = QtWidgets.QSlider(self)
        self.slid_ftest.setOrientation(QtCore.Qt.Horizontal)
        self.slid_ftest.setRange(-self.nzstep, self.nzstep)
        self.slid_ftest.setValue(gui_conf[f'dm{self.dmid}']['ftest_a0'])
        self.ftest_a0 = self.slid_ftest.value() * self.amax / self.nzstep

        # FTEST amplitude display label
        self.lbl_disp_ftest = QtWidgets.QLabel(self)
        self.lbl_disp_ftest.setText(f"{self.ftest_a0:0.3f}")

        # ------------------- ZERNIKE -----------------
        self.lbl_zer = []
        self.slid_zer = []
        self.lbl_disp_zer = []
        self.zer_a0 = np.zeros(self.nzer)

        znames = zer_names(1, self.nzer)
        self.zbank = zer_bank(1, self.nzer) #, tapered=True)
        self.zmap = np.zeros((dms, dms))

        for ii in range(self.nzer):
            # labels
            self.lbl_zer.append(QtWidgets.QLabel(self))
            self.lbl_zer[ii].setText(znames[ii])

            # sliders
            self.slid_zer.append(QtWidgets.QSlider(self))
            self.slid_zer[ii].setOrientation(QtCore.Qt.Horizontal)
            self.slid_zer[ii].setRange(-self.nzstep, self.nzstep)
            self.slid_zer[ii].setValue(
                gui_conf[f'dm{self.dmid}'][f'zer_{ii:02d}_a0'])

            # display labels
            self.lbl_disp_zer.append(QtWidgets.QLabel(self))
            self.lbl_disp_zer[ii].setText("0.000")

    # =========================================================================
    def apply_layout(self):
        clh = 28   # control line height
        px0 = 420  # x-origin of the panel
        sx0 = 500  # x-origin of the sliders
        lx0 = 760  # x-origin of the "amplitude" labels
        pwx = 420  # width of the panel
        zy0 = 180  # vertical origin of the zenike block
        
        self.lbl_live.setGeometry(QRect(0, 0, 420, clh))
        self.lbl_dmid.setGeometry(QRect(100, 450, 250, 60))
        self.gView_shm.setGeometry(QRect(10, 30, 400, 400))
        self.pB_reset.setGeometry(QRect(10, 470, 100, clh))

        self.lbl_ctrl.setGeometry(QRect(px0, 0, pwx, clh))
        self.chB_actv_flat.setGeometry(QRect(px0, 50, 60, clh))

        # cross
        self.chB_actv_cross.setGeometry(QRect(px0, 50 + clh, 60, clh))
        self.slid_cross.setGeometry(QRect(sx0, 50 + clh, 250, clh))
        self.lbl_disp_cross.setGeometry(QRect(lx0, 50 + clh, 50, clh))

        # F-test
        self.chB_actv_ftest.setGeometry(QRect(px0, 50 + 2 * clh, 60, clh))
        self.slid_ftest.setGeometry(QRect(sx0, 50 + 2 * clh, 250, clh))
        self.lbl_disp_ftest.setGeometry(QRect(lx0, 50 + 2 * clh, 50, clh))

        # Zernikes
        for ii in range(self.nzer):
            self.lbl_zer[ii].setGeometry(QRect(px0, zy0+clh*ii, 80, clh))
            self.slid_zer[ii].setGeometry(QRect(sx0, zy0+clh*ii, 250, clh))
            self.lbl_disp_zer[ii].setGeometry(QRect(lx0, zy0+clh*ii, 50, clh))

    # =========================================================================
    def setup_shm(self):
        shmfs = np.sort(glob.glob(f"/dev/shm/dm{self.dmid}disp*.im.shm"))
        shmf0 = f"/dev/shm/dm{self.dmid}.im.shm"
        self.nch = len(shmfs)

        self.shms = []
        for ii in range(self.nch):
            self.shms.append(shm(shmfs[ii], nosem=False))

        if self.nch != 0:
            self.shm0 = shm(shmf0, nosem=False)
        else:
            print("Shared memory structures unavailable. DM server started?")

    # =========================================================================
    def close_shm(self):
        for ii in range(self.nch):
            self.shms[ii].close(erase_file=False)
        for ii in range(self.nch):
            self.shms.pop(0)
        if self.nch != 0:
            self.shm0.close(erase_file=False)

    # =========================================================================
    def tab_widget_actions(self):
        self.pB_reset.clicked.connect(self.reset_DM_configuration)
        self.chB_actv_flat.stateChanged[int].connect(self.activate_flat)
        self.chB_actv_cross.stateChanged[int].connect(self.activate_cross)
        self.chB_actv_ftest.stateChanged[int].connect(self.activate_ftest)

        self.slid_cross.valueChanged[int].connect(self.activate_cross_slider)
        self.slid_ftest.valueChanged[int].connect(self.activate_ftest_slider)

        for ii in range(self.nzer):
            self.slid_zer[ii].valueChanged[int].connect(
                self.activate_zernike_sliders)

    # =========================================================
    def activate_zernike_sliders(self):
        global gui_conf
        a0 = self.amax / self.nzstep
        p0 = 0.5 / self.nzstep # special case for piston
        zmap = np.zeros((dms, dms))
        for ii in range(self.nzer):
            sld_val = self.slid_zer[ii].value()
            if ii == 0:
                # special case for piston only!
                self.zer_a0[ii] = p0 * sld_val
            else:
                self.zer_a0[ii] = a0 * sld_val
            gui_conf[f'dm{self.dmid}'][
                f'zer_{ii:02d}_a0'] = sld_val

            self.lbl_disp_zer[ii].setText(f"{self.zer_a0[ii]:.3f}")
            zmap += self.zer_a0[ii] * self.zbank[ii]
        if self.nch > 0:
            self.shms[2].set_data(zmap)
            self.shm0.post_sems(1)  # signal the DM to update itself

    # =========================================================
    def activate_flat(self):
        global gui_conf
        if self.nch == 0:
            return
        wdir = os.path.dirname(__file__)
        if self.chB_actv_flat.isChecked():
            flat_cmd = np.loadtxt(wdir+"/"+flat_cmd_files[self.dmid-1])
            self.shms[0].set_data(cmd_2_map2D(flat_cmd, fill=0.0))
            gui_conf[f'dm{self.dmid}']['flat_chbox'] = True
        else:
            self.shms[0].set_data(np.zeros((dms, dms)))
            gui_conf[f'dm{self.dmid}']['flat_chbox'] = False
        self.shm0.post_sems(1)  # signal the DM to update itself

    # =========================================================
    def activate_cross(self):
        global gui_conf
        ii0 = dms // 2 - 1
        a0 = self.cross_a0
        if self.chB_actv_cross.isChecked():
            if self.chB_actv_ftest.isChecked():
                self.chB_actv_ftest.setChecked(False)
            cross_cmd = np.zeros((dms, dms))
            cross_cmd[ii0:ii0+2, :] = a0
            cross_cmd[:, ii0:ii0+2] = a0
            if self.nch > 0:
                self.shms[1].set_data(cross_cmd)
            gui_conf[f'dm{self.dmid}']['cross_chbox'] = True
        else:
            if self.nch > 0:
                self.shms[1].set_data(np.zeros((dms, dms)))
            gui_conf[f'dm{self.dmid}']['cross_chbox'] = False
        if self.nch > 0:
            self.shm0.post_sems(1)  # signal the DM to update itself

    # =========================================================
    def activate_cross_slider(self):
        global gui_conf
        a0 = self.amax / self.nzstep
        self.cross_a0 = self.slid_cross.value() * a0
        gui_conf[f'dm{self.dmid}']['cross_a0'] = self.slid_cross.value()
        self.lbl_disp_cross.setText(f"{self.cross_a0:.3f}")
        self.chB_actv_cross.setChecked(True)
        if self.nch == 0:
            return
        self.activate_cross()

    # =========================================================
    def activate_ftest(self):
        global gui_conf
        if self.nch == 0:
            return

        if self.chB_actv_ftest.isChecked():
            if self.chB_actv_cross.isChecked():
                self.chB_actv_cross.setChecked(False)
            pattern = np.roll(ftest(dms, dms, 2), (-1, -1), axis=(0, 1))
            self.shms[1].set_data(self.ftest_a0 * pattern)
            gui_conf[f'dm{self.dmid}']['ftest_chbox'] = True
        else:
            self.shms[1].set_data(np.zeros((dms, dms)))
            gui_conf[f'dm{self.dmid}']['ftest_chbox'] = False
        self.shm0.post_sems(1)  # signal the DM to update itself

    # =========================================================================
    def activate_ftest_slider(self):
        global gui_conf
        a0 = self.amax / self.nzstep
        self.ftest_a0 = self.slid_ftest.value() * a0
        gui_conf[f'dm{self.dmid}']['ftest_a0'] = self.slid_ftest.value()
        self.lbl_disp_ftest.setText(f"{self.ftest_a0:.3f}")
        self.chB_actv_ftest.setChecked(True)
        if self.nch > 0:
            self.activate_ftest()

    # =========================================================================
    def reset_DM_configuration(self):
        ''' -------------------------------------------------------------------
        Not sure why, but the reset operation doesn't work that great.
        ------------------------------------------------------------------- '''
        global gui_conf
        initialize_gui_configuration(self.dmid)
        self.update_tab_config()
        if self.nch > 0:
            self.shm0.post_sems(1)

    # =========================================================================
    def update_img(self):
        if self.nch > 0:
            self.data_img = self.shm0.get_data()
        else:
            # self.data_img = np.random.randn(dms, dms)
            self.data_img = np.zeros((dms, dms))
        self.imv_data.setImage(arr2im(self.data_img, vmin=0, vmax=1), border=2)

    # =========================================================================
    def update_tab_config(self):
        global gui_conf
        i0 = self.dmid
        a0 = self.amax / self.nzstep
        p0 = 0.5 / self.nzstep # special case for piston
        
        self.chB_actv_flat.setChecked(gui_conf[f'dm{i0}']['flat_chbox'])
        self.chB_actv_cross.setChecked(gui_conf[f'dm{i0}']['cross_chbox'])
        self.chB_actv_ftest.setChecked(gui_conf[f'dm{i0}']['ftest_chbox'])

        self.slid_cross.setValue(gui_conf[f'dm{i0}']['cross_a0'])
        self.slid_ftest.setValue(gui_conf[f'dm{i0}']['ftest_a0'])

        for ii in range(self.nzer):
            step_val = gui_conf[f'dm{i0}'][f'zer_{ii:02d}_a0']
            self.slid_zer[ii].setValue(step_val)
            if ii == 0:
                self.zer_a0[ii] = p0 * step_val
            else:
                self.zer_a0[ii] = a0 * step_val
            self.lbl_disp_zer[ii].setText(f"{self.zer_a0[ii]:.3f}")

# =============================================================================
# =============================================================================
class MyMultiTabWidget(QWidget):
    def __init__(self, parent): 
        super(QWidget, self).__init__(parent)

        # ---------------------------------------------------------------------
        #                              top menu
        # ---------------------------------------------------------------------
        self.actionOpen = QtWidgets.QAction(
            QtGui.QIcon(":/images/open.png"), "&Open...", self)

        self.actionQuit = QtWidgets.QAction(
            QtGui.QIcon(":/images/open.png"), "&Quit", self)

        self.actionQuit.triggered.connect(self.close_program)
        self.actionQuit.setShortcut('Ctrl+Q')

        self.menu = parent.menuBar()
        file_menu = self.menu.addMenu("&File")
        file_menu.addAction(self.actionQuit)

        self.layout = QtWidgets.QVBoxLayout(self)
        
        # ---------------------------------------------------------------------
        #                             tab screen
        # ---------------------------------------------------------------------
        self.qtab = QtWidgets.QTabWidget()
        self.tabs = []
        
        for ii in range(ndm):
            self.tabs.append(DMTabWidget(self, ii+1))
            self.qtab.addTab(self.tabs[ii], f"DM #{ii+1}")
            self.tabs[ii].apply_layout()
            self.tabs[ii].tab_widget_actions()
            self.tabs[ii].setup_shm()
            self.tabs[ii].update_tab_config()

        self.tabs.append(QtWidgets.QWidget())
        self.qtab.addTab(self.tabs[4], "EXTRA...")

        # Add qtab to widget
        self.layout.addWidget(self.qtab) 

        self.tabs[2].update_img()

    def close_shm(self):
        for ii in range(ndm):
            self.tabs[ii].close_shm()

    # called when using menu or ctrl-Q
    def close_program(self):
        global gui_conf
        self.close_shm()

        with open(f'{conf_dir}MDM_lab_GUI.json', 'w') as json_config:
            json.dump(gui_conf, json_config, indent=2)        
        sys.exit()

# ==========================================================
# ==========================================================
def main():
    global myqt, gui_conf
    myqt = QtMain()

    try:
        with open(conf_dir + "MDM_lab_GUI.json") as json_config:
            gui_conf = json.load(json_config)

    except FileNotFoundError:
        initialize_gui_configuration()
        print("No prior GUI configuration file found.")

    gui = App()
    gui.show()
    myqt.mainloop()
    myqt.gui_quit()

# ==========================================================
# ==========================================================
def initialize_gui_configuration(dmid=None):
    '''Initializes the GUI configuration dictionary.

    Called when pressing the RESET button
    '''
    global gui_conf
    if dmid is None:
        for ii in range(ndm):
            gui_conf[f'dm{ii+1}'] = {}
            gui_conf[f'dm{ii+1}']['flat_chbox'] = False
            gui_conf[f'dm{ii+1}']['cross_chbox'] = False
            gui_conf[f'dm{ii+1}']['ftest_chbox'] = False
            gui_conf[f'dm{ii+1}']['cross_a0'] = 0
            gui_conf[f'dm{ii+1}']['ftest_a0'] = 0
            for jj in range(nzer):
                gui_conf[f'dm{ii+1}'][f'zer_{jj:02d}_a0'] = 0
    else:
        gui_conf[f'dm{dmid}']['flat_chbox'] = False
        gui_conf[f'dm{dmid}']['cross_chbox'] = False
        gui_conf[f'dm{dmid}']['ftest_chbox'] = False
        gui_conf[f'dm{dmid}']['cross_a0'] = 0
        gui_conf[f'dm{dmid}']['ftest_a0'] = 0
        for jj in range(nzer):
            gui_conf[f'dm{dmid}'][f'zer_{jj:02d}_a0'] = 0


# ==========================================================
# ==========================================================
if __name__ == '__main__': 
    parser = argparse.ArgumentParser(
        prog='asgard_lab_MDM_controller',
        description='A lab GUI based controller for *all* ASGARD DMs',
        epilog='Ensure that the DM server is running!')

    args = parser.parse_args()
    main()
