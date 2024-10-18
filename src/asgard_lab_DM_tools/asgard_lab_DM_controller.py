#!/usr/bin/env python3

from xaosim.QtMain import QtMain
from xaosim.shmlib import shm
from xaosim.zernike import zer_mode_bank_2D as zer_bank
from xaosim.zernike import zer_name_list as zer_names
from xaosim.pupil import F_test_figure as ftest

import numpy as np
import matplotlib.cm as cm

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow
# from PyQt5.QtGui import QImage

import pyqtgraph as pg
from pyqtgraph import PlotWidget

import sys
import os
import glob
import json
import argparse

# =====================================================================
# =====================================================================
home = os.getenv('HOME')
myqt = 0  # myqt is a global variable
dms = 12  # the DM size. Could be read from shared memory
dmid = 0  # the DM identifier (should be 1, 2, 3 or 4)
gui_conf = {}  # dictionary to keep track of checkbox & sliders status

# home = os.getenv('HOME')
# conf_dir = next(iter(fpao_tools.__path__))+"/../config/"

def initialize_gui_configuration():
    '''Initializes the GUI configuration dictionary.

    Called when pressing the RESET button
    '''
    global gui_conf
    gui_conf['flat_checkbox'] = False
    gui_conf['cross_checkbox'] = False
    gui_conf['ftest_checkbox'] = False
    gui_conf['cross_amplitude'] = 0
    gui_conf['ftest_amplitude'] = 0
    return

def main():
    global myqt
    myqt = QtMain()

    global gui_conf
    try:
        with open(f"gui_config_{dmid}.json") as json_config:
            print("GUI config file found: restoring previous GUI state")
            gui_conf = json.load(json_config)
    except FileNotFoundError:
        print("No saved GUI status file found")
        initialize_gui_configuration()


    gui = MyWindow()

    gui.show()
    myqt.mainloop()
    myqt.gui_quit()
    print("DONE!")
    with open('gui_config.json', 'w') as json_config:
        json.dump(gui_conf, json_config, indent=2)
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
    arr2 = arr.astype('float').T
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


def cmd_2_map2D(cmd, fill=np.nan):
    '''Convert a 139 cmd into a 2D DM map for display.

    Just need to add the four corners (0 or nan) and reshape
    Parameters:
    - cmd  : 1D numpy array of 139 components
    - fill : filling values for corners (default = np.nan)
    '''
    return np.insert(cmd, [0, 10, 130, 140], fill).reshape((dms, dms))


# =====================================================================
#                           interface design
# =====================================================================
class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        wsx, wsy = 900, 600  # window size
        clh = 28             # control-line height
        self.nzer = 11       # number of zernike modes to work with
        self.amax = 0.4      # max. modulation amplitude
        self.nzstep = 20     # number of steps for Zernike sliders
        # title font
        font1 = QtGui.QFont()
        font1.setPointSize(12)
        font1.setBold(True)

        font2 = QtGui.QFont()
        font2.setPointSize(48)
        font2.setBold(True)
        
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(wsx, wsy)
        MainWindow.setMinimumSize(QtCore.QSize(800, 600))
        MainWindow.setMaximumSize(QtCore.QSize(800, 600))

        # ======== left-hand panel =======
        self.lbl_live = QtWidgets.QLabel(MainWindow)
        self.lbl_live.setObjectName("lbl_live")
        self.lbl_live.setGeometry(QtCore.QRect(0, 0, 420, 28))
        self.lbl_live.setText(f"DM live status {dmid}")
        self.lbl_live.setFont(font1)
        self.lbl_live.setAlignment(QtCore.Qt.AlignCenter)

        # the shared memory viewer
        self.gView_shm = PlotWidget(MainWindow)
        self.gView_shm.setObjectName("gView_shm")
        self.gView_shm.setGeometry(QtCore.QRect(10, 30, 400, 400))
        self.gView_shm.hideAxis('left')
        self.gView_shm.hideAxis('bottom')

        self.imv_data = pg.ImageItem()
        self.overlay = pg.GraphItem()

        self.gView_shm.addItem(self.imv_data)

        self.pB_test = QtWidgets.QPushButton(MainWindow)
        self.pB_test.setObjectName("pB_test")
        self.pB_test.setGeometry(QtCore.QRect(10, wsy-(clh+20), 100, clh))
        self.pB_test.setToolTip("Reset the GUI to neutral state")
        self.pB_test.setText("RESET")

        self.lbl_dmid = QtWidgets.QLabel(MainWindow)
        self.lbl_dmid.setObjectName("lbl_dmid")
        self.lbl_dmid.setGeometry(QtCore.QRect(100, 450, 250, 60))
        self.lbl_dmid.setText(f"DM #{dmid}")
        self.lbl_dmid.setFont(font2)
        self.lbl_dmid.setAlignment(QtCore.Qt.AlignCenter)

        
        # ======== right-hand panel =======
        px0 = 420  # x-origin of the panel
        sx0 = 500  # x-origin of the sliders
        lx0 = 760  # x-origin of the "amplitude" labels
        pwx = 420  # width of the panel

        self.lbl_ctrl = QtWidgets.QLabel(MainWindow)
        self.lbl_ctrl.setObjectName("lbl_ctrl")
        self.lbl_ctrl.setGeometry(QtCore.QRect(px0, 0, pwx, clh))
        self.lbl_ctrl.setText("DM control tools")
        self.lbl_ctrl.setFont(font1)
        self.lbl_ctrl.setAlignment(QtCore.Qt.AlignCenter)

        # activation checkbox for FLAT
        self.chB_actv_flat = QtWidgets.QCheckBox(MainWindow)
        self.chB_actv_flat.setObjectName("chB_actv_flat")
        self.chB_actv_flat.setGeometry(QtCore.QRect(px0, 50, 60, clh))
        self.chB_actv_flat.setText("Flat")

        # --------------------- CROSS -----------------
        # activation checkbox for CROSS
        self.chB_actv_cross = QtWidgets.QCheckBox(MainWindow)
        self.chB_actv_cross.setObjectName("chB_actv_piston")
        self.chB_actv_cross.setGeometry(QtCore.QRect(px0, 50 + clh, 60, clh))
        self.chB_actv_cross.setText("Cross")

        # slider for CROSS amplitude
        self.slid_cross = QtWidgets.QSlider(MainWindow)
        self.slid_cross.setObjectName("slid_cross")
        self.slid_cross.setGeometry(
            QtCore.QRect(sx0, 50 + clh, 250, clh))
        self.slid_cross.setOrientation(QtCore.Qt.Horizontal)
        self.slid_cross.setRange(-self.nzstep, self.nzstep)
        self.slid_cross.setValue(gui_conf['cross_amplitude'])
        self.cross_a0 = self.slid_cross.value() * self.amax / self.nzstep

        # CROSS amplitude display label
        self.lbl_disp_cross = QtWidgets.QLabel(MainWindow)
        self.lbl_disp_cross.setObjectName("lbl_disp_cross")
        self.lbl_disp_cross.setGeometry(
            QtCore.QRect(lx0, 50 + clh, 50, clh))
        self.lbl_disp_cross.setText(f"{self.cross_a0:0.2f}")

        # --------------------- FTEST -----------------
        # activation checkbox for FTEST
        self.chB_actv_ftest = QtWidgets.QCheckBox(MainWindow)
        self.chB_actv_ftest.setObjectName("chB_actv_ftest")
        self.chB_actv_ftest.setGeometry(
            QtCore.QRect(px0, 50 + 2 * clh, 60, clh))
        self.chB_actv_ftest.setText("F-test")

        # slider for FTEST amplitude
        self.slid_ftest = QtWidgets.QSlider(MainWindow)
        self.slid_ftest.setObjectName("slid_ftest")
        self.slid_ftest.setGeometry(
            QtCore.QRect(sx0, 50 + 2 * clh, 250, clh))
        self.slid_ftest.setOrientation(QtCore.Qt.Horizontal)
        self.slid_ftest.setRange(-self.nzstep, self.nzstep)
        self.slid_ftest.setValue(gui_conf['ftest_amplitude'])
        self.ftest_a0 = self.slid_ftest.value() * self.amax / self.nzstep

        # FTEST amplitude display label
        self.lbl_disp_ftest = QtWidgets.QLabel(MainWindow)
        self.lbl_disp_ftest.setObjectName("lbl_disp_ftest")
        self.lbl_disp_ftest.setGeometry(
            QtCore.QRect(lx0, 50 + 2 * clh, 50, clh))
        self.lbl_disp_ftest.setText(f"{self.ftest_a0:0.2f}")

        # ------------------- ZERNIKE -----------------
        zy0 = 180  # vertical origin of the zenike block
        self.lbl_zer = []
        self.slid_zer = []
        self.lbl_disp_zer = []
        self.zer_a0 = np.zeros(self.nzer)

        znames = zer_names(1, self.nzer)
        self.zbank = zer_bank(dms, 1, self.nzer, limit=False)
        self.zmap = np.zeros((dms, dms))

        for ii in range(self.nzer):
            # labels
            self.lbl_zer.append(QtWidgets.QLabel(MainWindow))
            self.lbl_zer[ii].setObjectName(f"lbl_zer_{ii:02d}")
            self.lbl_zer[ii].setGeometry(
                QtCore.QRect(px0, zy0+clh*ii, 80, clh))
            self.lbl_zer[ii].setText(znames[ii])

            # sliders
            self.slid_zer.append(QtWidgets.QSlider(MainWindow))
            self.slid_zer[ii].setObjectName("slid_zer_{ii:02d}")
            self.slid_zer[ii].setGeometry(
                QtCore.QRect(sx0, zy0+clh*ii, 250, clh))
            self.slid_zer[ii].setOrientation(QtCore.Qt.Horizontal)
            self.slid_zer[ii].setRange(-self.nzstep, self.nzstep)
            self.slid_zer[ii].setValue(0)

            # display labels
            self.lbl_disp_zer.append(QtWidgets.QLabel(MainWindow))
            self.lbl_disp_zer[ii].setObjectName(f"lbl_disp_zer_{ii:02d}")
            self.lbl_disp_zer[ii].setGeometry(
                QtCore.QRect(lx0, zy0+clh*ii, 50, clh))
            self.lbl_disp_zer[ii].setText("0.00")
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "DM lab controler"))
        self.lbl_live.setText(_translate("MainWindow", f"DM live status {dmid}"))

# =====================================================================
#                        Main GUI object
# =====================================================================
class MyWindow(QMainWindow):
    def __init__(self):
        self.vmin = False
        self.vmax = False
        self.pwr = 1.0
        self.mycmap = cm.viridis
        super(MyWindow, self).__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.data_img = np.zeros((dms, dms))
        # ==============================================
        #                 SHM setup
        # ==============================================
        shmfs = np.sort(glob.glob(f"/dev/shm/dm{dmid}disp*.im.shm"))
        shmf0 = f"/dev/shm/dm{dmid}.im.shm"
        print(f"shmf0 = {shmf0}")
        print(shmfs)
        self.nch = len(shmfs)

        self.shms = []
        for ii in range(self.nch):
            self.shms.append(shm(shmfs[ii]))
            print(f"added: {shmfs[ii]}")  # % (shmfs[ii],))

        # breakpoint()
        if self.nch != 0:
            self.shm0 = shm(shmf0)
        else:
            print("Shared memory structures unavailable. DM server started?")

        # ==============================================
        #             GUI widget actions
        # ==============================================
        self.ui.pB_test.clicked.connect(self.reset_gui_configuration)
        self.ui.chB_actv_flat.stateChanged[int].connect(self.activate_flat)
        self.ui.chB_actv_cross.stateChanged[int].connect(self.activate_cross)
        self.ui.chB_actv_ftest.stateChanged[int].connect(self.activate_ftest)

        self.ui.slid_cross.valueChanged[int].connect(
            self.activate_cross_slider)

        self.ui.slid_ftest.valueChanged[int].connect(
            self.activate_ftest_slider)

        for ii in range(self.ui.nzer):
            self.ui.slid_zer[ii].valueChanged[int].connect(
                self.activate_zernike_sliders)

        # ==============================================

        self.update_gui_configuration()
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.refresh_all)
        self.timer.start(200)

    # =========================================================
    def update_gui_configuration(self):
        '''Updates the GUI status (checkboxes & sliders)

        According to the information available in the gui_conf
        dictionary.
        '''
        self.ui.chB_actv_flat.setChecked(gui_conf['flat_checkbox'])
        self.ui.chB_actv_cross.setChecked(gui_conf['cross_checkbox'])
        self.ui.chB_actv_ftest.setChecked(gui_conf['ftest_checkbox'])
        self.ui.slid_cross.setValue(gui_conf['cross_amplitude'])
        self.ui.slid_ftest.setValue(gui_conf['ftest_amplitude'])

        for ii in range(self.ui.nzer):
            self.ui.slid_zer[ii].setValue(0)

    # =========================================================
    def reset_gui_configuration(self):
        '''
        '''
        # global gui_conf
        # initial configuration of the GUI
        initialize_gui_configuration()
        self.update_gui_configuration()

    # =========================================================
    def activate_zernike_sliders(self):
        if self.nch == 0:
            return

        a0 = self.ui.amax / self.ui.nzstep
        zmap = np.zeros((dms, dms))
        for ii in range(self.ui.nzer):
            self.ui.zer_a0[ii] = a0 * self.ui.slid_zer[ii].value()
            self.ui.lbl_disp_zer[ii].setText(f"{self.ui.zer_a0[ii]:.2f}")
            zmap += self.ui.zer_a0[ii] * self.ui.zbank[ii]
        self.shms[2].set_data(zmap)

        pass

    # =========================================================
    def select_flat_cmd(wdir='./'):
        '''Matches a DM flat command file to a DM id #.

        Returns the name of the file in the work directory.
        '''
        flat_cmd_files = [
            "17DW019#113_FLAT_MAP_COMMANDS.txt",
            "17DW019#093_FLAT_MAP_COMMANDS.txt",
            "17DW019#xxx_FLAT_MAP_COMMANDS.txt",
            "17DW019#yyy_FLAT_MAP_COMMANDS.txt"]
        return wdir + flat_cmd_files[dmid - 1]

    # =========================================================
    def activate_flat(self):
        if self.nch == 0:
            return

        if self.ui.chB_actv_flat.isChecked():
            # flat_cmd = np.loadtxt("./17DW019#113_FLAT_MAP_COMMANDS.txt")
            flat_cmd = np.loadtxt(select_flat_cmd())
            self.shms[0].set_data(cmd_2_map2D(flat_cmd, fill=0.0))
            gui_conf['flat_checkbox'] = True
        else:
            self.shms[0].set_data(np.zeros((dms, dms)))
            gui_conf['flat_checkbox'] = False

    # =========================================================
    def activate_cross(self):
        if self.nch == 0:
            return

        ii0 = dms // 2 - 1
        a0 = self.ui.cross_a0
        if self.ui.chB_actv_cross.isChecked():
            if self.ui.chB_actv_ftest.isChecked():
                self.ui.chB_actv_ftest.setChecked(False)
            cross_cmd = np.zeros((dms, dms))
            cross_cmd[ii0:ii0+2, :] = a0
            cross_cmd[:, ii0:ii0+2] = a0
            self.shms[1].set_data(cross_cmd)
            gui_conf['cross_checkbox'] = True
        else:
            self.shms[1].set_data(np.zeros((dms, dms)))
            gui_conf['cross_checkbox'] = False

    # =========================================================
    def activate_cross_slider(self):
        if self.nch == 0:
            return

        a0 = self.ui.amax / self.ui.nzstep
        self.ui.cross_a0 = self.ui.slid_cross.value() * a0
        gui_conf['cross_amplitude'] = self.ui.slid_cross.value()
        self.ui.lbl_disp_cross.setText(f"{self.ui.cross_a0:.2f}")
        self.ui.chB_actv_cross.setChecked(True)
        self.activate_cross()

    # =========================================================
    def activate_ftest(self):
        if self.nch == 0:
            return

        if self.ui.chB_actv_ftest.isChecked():
            if self.ui.chB_actv_cross.isChecked():
                self.ui.chB_actv_cross.setChecked(False)
            pattern = np.roll(ftest(dms, dms, 2), (-1, -1), axis=(0, 1))
            self.shms[1].set_data(self.ui.ftest_a0 * pattern)
            gui_conf['ftest_checkbox'] = True
        else:
            self.shms[1].set_data(np.zeros((dms, dms)))
            gui_conf['ftest_checkbox'] = False

    # =========================================================
    def activate_ftest_slider(self):
        if self.nch == 0:
            return

        a0 = self.ui.amax / self.ui.nzstep
        self.ui.ftest_a0 = self.ui.slid_ftest.value() * a0
        gui_conf['ftest_amplitude'] = self.ui.slid_ftest.value()
        self.ui.lbl_disp_ftest.setText(f"{self.ui.ftest_a0:.2f}")
        self.ui.chB_actv_ftest.setChecked(True)
        self.activate_ftest()

    # =========================================================
    def refresh_all(self):
        self.refresh_img()
        pass

    # =========================================================
    def refresh_img(self):
        if self.nch > 0:
            self.data_img = self.shm0.get_data()  # combined channel
            # self.data_img = self.shms[0].get_data()  # combined channel
        self.ui.imv_data.setImage(
            arr2im(self.data_img, vmax=1, cmap=self.mycmap),
            border=2)

    # =========================================================
    def closeEvent(self, event):
        # freeing all shared memory structures
        for ii in range(self.nch):
            self.shms[ii].close(erase_file=False)
        for ii in range(self.nch):
            self.shms.pop(0)

        with open(f'gui_config_{dmid}.json', 'w') as json_config:
            json.dump(gui_conf, json_config, indent=2)
        print("end of program")

        sys.exit()

# =========================================================
def start_gui():
    '''Entry point when the program is executed from the CLI

    Basic parsing of input and launch of a GUI
    '''
    global dmid
    parser = argparse.ArgumentParser(
        prog='asgard_lab_DM_controller',
        description='A lab GUI based controller for the ASGARD DMs',
        epilog='Ensure that the corresponding DM server is running!')
    
    parser.add_argument('dmid', type=int, nargs=1, choices=range(1, 5),
                        help='The DM identifier!')
    
    args = parser.parse_args()
    dmid = int(args.dmid[0])
    main()

# ==========================================================
# ==========================================================
if __name__ == "__main__":
    start_gui()
