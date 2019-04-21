# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 10:01:53 2019

@author: Ian
"""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QDateTimeEdit,
                             QDial, QDialog, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QLineEdit, QProgressBar,
                             QPushButton, QRadioButton, QScrollBar,
                             QSizePolicy, QSlider, QSpinBox, QStyleFactory,
                             QTableWidget, QTabWidget, QTextEdit, QVBoxLayout,
                             QWidget, QMessageBox, QFormLayout, QStackedWidget,
                             QFrame, QMainWindow, QDockWidget)
import sys
from VISA_Communications import VisaLaser
import time
from math import trunc


def truncate(number, decimals=0):
    if decimals < 0:
        raise ValueError('Cannot truncate to negative decimals ({})'
                         .format(decimals))
    elif decimals == 0:
        return trunc(number)
    else:
        factor = float(10 ** decimals)
        return trunc(number * factor) / factor


# FIXME: Add a raster target check for manual control
class LaserStatusControl(QWidget):

    def __init__(self, laser):
        super().__init__()

        # Set up permissible modes list
        self.inModes = {'EGY NGR': 'Energy', 'HV': 'HV'}
        self.outModes = {'Energy': 'EGY NGR', 'HV': 'HV'}

        # Pull in parameters
        self.laser = laser

        # Create widgets and other GUI elements
        self.modeSelLabel = QLabel('Mode: ')
        self.modeSel = QComboBox()
        self.egyLabel = QLabel('Energy: ')
        self.egyVal = QLineEdit(self.laser.rd_energy())
        self.hvLabel = QLabel('HV: ')
        self.hvVal = QLineEdit(self.laser.rd_hv())
        self.reprateLabel = QLabel('Reprate: ')
        self.reprateVal = QLineEdit(self.laser.rd_reprate())
        self.btnOnOff = QPushButton("Start Laser")
        self.terminal = QLineEdit()
        self.hbox = QHBoxLayout()
        self.vbox = QVBoxLayout()
        self.updateTimer = QTimer()

        # Define/Create widgets for laser status and control
        self.title = QLabel('Laser Status')

        # Run function to adjust widget parameters/build the LSC
        self.init_ui()

    def init_ui(self):
        """Manipulate and adjust laser status and manual control widgets"""
        # Create and format title for LSC block
        self.title.setAlignment(Qt.AlignCenter)
        # FIXME: Change how this is handled to be general to other instances
        self.title.setFont(QFont('Arial', 24, QFont.Bold))

        # Mode Selection Box. Will default to current laser running mode
        self.modeSel.addItems(self.inModes.values())
        # FIXME: Might want to force the laser into EGY NGR or HV mode if any
        # other mode is detected (i.e. index=-1)
        index = self.modeSel.findText(self.inModes[self.laser.rd_mode()])
        self.modeSel.setCurrentIndex(index)
        self.modeSel.currentTextChanged.connect(self.change_mode)

        # Energy reading/setting box: while laser is running, will display
        # last pulse avg value, otherwise will display setting for egy mode
        # and last pulse energy for hv mode.
        self.egyVal.returnPressed.connect(self.set_energy)

        # HV setting box: Displays currently set HV for HV mode. For EGY mode
        # displays the HV set by the laser to match energy setting.
        self.hvVal.returnPressed.connect(self.set_hv)

        # Reprate setting box: Displays current reprate. Will display "EXT" if
        # the laser is set to external triggering
        self.reprateVal.returnPressed.connect(self.set_reprate)

        # Start Stop Button
        # self.btnOnOff.setAlignment(Qt.AlignCenter)
        self.btnOnOff.clicked.connect(self.change_btn_on_off)

        # DEBUG: Create a pause LSC update button
        # self.isLSCUpdating = True
        # self.btnPauseUpdate = QPushButton("Pause LSC Updates")
        # self.btnPauseUpdate.clicked.connect(self.pause_LSC)

        # Terminal box for debug
        self.terminal.setPlaceholderText('Enter a command here')
        self.terminal.returnPressed.connect(self.terminal_send)

        # Create a Horizontal Layout to contain the value and setting boxes
        self.hbox.addWidget(self.modeSelLabel)
        self.hbox.addWidget(self.modeSel)
        self.hbox.addWidget(self.egyLabel)
        self.hbox.addWidget(self.egyVal)
        self.hbox.addWidget(self.hvLabel)
        self.hbox.addWidget(self.hvVal)
        self.hbox.addWidget(self.reprateLabel)
        self.hbox.addWidget(self.reprateVal)

        # Create a vertical box to set up title and LSC boxes
        self.vbox.addWidget(self.title)
        self.vbox.addLayout(self.hbox)
        self.vbox.addWidget(self.btnOnOff)
        # self.vbox.addWidget(self.btnPauseUpdate)
        self.vbox.addWidget(self.terminal)

        self.setLayout(self.vbox)
        self.change_mode(self.modeSel.currentText())

        # Moved from main() into the function
        self.updateTimer.timeout.connect(self.update_lsc)
        self.updateTimer.start(int(1000 / int(self.laser.rd_reprate())))

    # Updater for the laser status readouts. Only updates for fields that are
    # not currently selected.
    def update_lsc(self):
        if not self.egyVal.hasFocus():
            self.egyVal.setText(self.laser.rd_energy())

        if not self.hvVal.hasFocus():
            self.hvVal.setText(self.laser.rd_hv())

        if not self.reprateVal.hasFocus():
            if self.laser.rd_trigger() == 'INT':
                self.reprateVal.setText(self.laser.rd_reprate())
                self.reprateVal.setDisabled(False)
            elif self.laser.rd_trigger() == 'EXT':
                self.reprateVal.setDisabled(True)
                self.reprateVal.setText('External')

    # Sends the command that was typed into the terminal.
    def terminal_send(self):
        self.terminal.setText(self.laser.query(self.terminal.text()))
        print("Terminal Command Sent")

    # Sends a command to the laser to change mode. Also sets which parameters
    # are editable from the LSC.
    def change_mode(self, mode):
        self.laser.set_mode(self.outModes[mode])
        if self.outModes[mode] == 'HV':
            self.egyVal.setDisabled(True)
            self.hvVal.setDisabled(False)
        if self.outModes[mode] == 'EGY NGR':
            self.egyVal.setDisabled(False)
            self.hvVal.setDisabled(True)

    def change_btn_on_off(self):
        on_opmodes = ['ON', 'OFF,WAIT']
        # On button press stops the timer that updates the display so that
        # we don't see timeouts on pressing the button to stop/start
        self.updateTimer.stop()
        time.sleep(0.01)

        if self.laser.rd_opmode() in on_opmodes:
            self.laser.off()
            self.btnOnOff.setText('&Start Laser')
        elif self.laser.rd_opmode() == 'OFF:31':
            timeout_clear = QMessageBox.question(self, 'Laser Status: Timeout',
                                                 "Press Ok to clear laser\
                                                 timeout and start lasing.",
                                                 QMessageBox.Ok |
                                                 QMessageBox.Cancel,
                                                 QMessageBox.Cancel)
            if timeout_clear == QMessageBox.Ok:
                self.laser.set_timeout(False)
                time.sleep(0.01)
                self.laser.on()
                self.btnOnOff.setText('Stop Laser')
            elif timeout_clear == QMessageBox.Cancel:
                pass

        else:
            self.laser.on()
            self.btnOnOff.setText('Stop Laser')

        # Re-enables the updater for the LSC
        time.sleep(0.01)
        self.updateTimer.start(int(1000 / int(self.laser.rd_reprate())))

    # def pause_LSC(self):
    #     self.isLSCUpdating = not self.isLSCUpdating
    #     if self.isLSCUpdating:
    #         self.updateTimer.stop()
    #     elif not self.isLSCUpdating:
    #         self.updateTimer.start(1000 / int(self.laser.rd_reprate()))

    def set_energy(self):
        self.laser.set_energy(self.egyVal.text())
        self.egyVal.clearFocus()

    def set_hv(self):
        self.laser.set_hv(self.hvVal.text())
        self.hvVal.clearFocus()

    def set_reprate(self):
        self.laser.set_reprate(self.reprateVal.text())
        self.reprateVal.clearFocus()


class DepControlBox(QWidget):

    def __init__(self, laser):
        super().__init__()
        self.modeList = ["Standard Deposition",
                         "Super Lattice",
                         "PLID",
                         "Equilibration"]
        self.laser = laser
        # Initialize program interaction controls
        self.programModeComboLbl = QLabel("Mode:")
        self.programModeCombo = QComboBox()
        self.programModeCombo.addItems(self.modeList)
        self.loadBtn = QPushButton("Load...")
        self.saveBtn = QPushButton("Save...")
        self.runCurrentBtn = QPushButton("Run")
        self.leftCol = QVBoxLayout()
        self.hbox = QHBoxLayout()

        # Connect Buttons to their functions
        self.runCurrentBtn.clicked.connect(self.run_step)
        # FIXME: The obvious way to do this is to use pickle
        # self.saveBtn.clicked.connect(self.save_parameters)
        # FIXME: Build in the ability to load from a dictionary to the Structure parameter form
        # self.loadBtn.clicked.connect(self.load_parameters)

        # Create the list of steps/deposition dictionary to use
        self.paramStack = QStackedWidget()
        # FIXME: Need this to not be hardcoded for the dictionary or maybe it should be.
        self.stdDepWidget = StructureParamForm(StackParamForm({"Main": DepositionStepForm("Main Deposition", 1),
                                                               "Second": DepositionStepForm("Test", 2)}), False)
        # Set up UI elements
        self.init_ui()

    def init_ui(self):
        # Add all elements to the left column that will have program interaction controls
        self.leftCol.insertStretch(1)
        self.leftCol.addWidget(self.programModeComboLbl)
        self.leftCol.addWidget(self.programModeCombo)
        self.leftCol.addSpacing(50)
        self.leftCol.addWidget(self.loadBtn)
        self.leftCol.addWidget(self.saveBtn)
        self.leftCol.addSpacing(50)
        self.leftCol.addWidget(self.runCurrentBtn)
        self.leftCol.insertStretch(1)

        # Create a stacked widget that will contain the parameter settings for
        # the program that is loaded/being edited
        self.paramStack.addWidget(self.stdDepWidget)
        self.paramStack.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.paramStack.setLineWidth(2)
        # FIXME: Need to add other parameter widgets to the stack

        # Create the horizontal layout that will contain the program interaction
        # control column and the parameter setting stack
        self.hbox.addLayout(self.leftCol)
        self.hbox.addWidget(self.paramStack)
        self.setLayout(self.hbox)

    def run_step(self):
        deposition = Deposition(self.paramStack.currentWidget(), self.laser)
        deposition.start()


class DepositionStepForm(QVBoxLayout):

    def __init__(self, step_title, layer_code):
        super().__init__()

        # Pull in parameters as variables
        self.stepTitle = step_title + " Parameters"
        self.layerCode = layer_code

        # Set up extra parts needed to create an equilibrium step
        if self.layerCode == 0:
            self.formatStr = "Eq "
            self.runEquilCheck = QCheckBox()
            self.rasterCheck = QCheckBox()

        elif 1 <= self.layerCode <= 3:
            self.formatStr = "L{} ".format(self.layerCode)

        # Initialize controls for all types of deposition step form
        self.reprateLine = QLineEdit()
        self.pulseCountLine = QLineEdit()
        self.depTimeLine = QLineEdit()
        self.energyLine = QLineEdit()
        self.title = QLabel(self.stepTitle)
        self.form = QFormLayout()

        self.init_form()

    def init_form(self):

        # Set up the title and form for the main deposition settings
        self.title.setFont(QFont('Arial', 12, QFont.Bold))
        if self.layerCode == 0:
            self.form.addRow("Run Equilibration", self.runEquilCheck)
            self.form.addRow("Raster Target (Applies to all Steps)", self.rasterCheck)
        self.form.addRow("{}Reprate: ".format(self.formatStr),
                         self.reprateLine)
        self.form.addRow("{}Pulses: ".format(self.formatStr),
                         self.pulseCountLine)
        self.form.addRow("{}Time: ".format(self.formatStr),
                         self.depTimeLine)
        self.form.addRow("{}Energy: ".format(self.formatStr),
                         self.energyLine)

        self.addWidget(self.title)
        self.addLayout(self.form)

    def return_layer_params(self):
        if self.layerCode == 0:
            return {"Layer Code": self.layerCode,
                    "Run Eq": self.runEquilCheck.isChecked(),
                    "Raster": self.rasterCheck.isChecked(),
                    "Reprate": self.reprateLine.text(),
                    "Pulses": self.pulseCountLine.text(),
                    "Time": self.depTimeLine.text(),
                    "Energy": self.energyLine.text()}
        else:
            return {"Layer Code": self.layerCode,
                    "Run Eq": None,
                    "Raster": None,
                    "Reprate": self.reprateLine.text(),
                    "Pulses": self.pulseCountLine.text(),
                    "Time": self.depTimeLine.text(),
                    "Energy": self.energyLine.text()}


class StackParamForm(QVBoxLayout):

    def __init__(self, layer_dict):  # FIXME: Need another function to build the layer dict
        super().__init__()
        self.dictLayers = layer_dict
        self.init_widget()

    def init_widget(self):
        for key in self.dictLayers:
            self.addLayout(self.dictLayers[key])

    def return_stack_params(self):
        stack_params = {}

        for key in self.dictLayers:
            layer_params = self.dictLayers[key].return_layer_params()

            # # FIXME: Commented for posterity, changing dep building structure so that the stack
            # # will never have an equilibration step in it. Equilibration will always be set
            # # in the StructureParamForm
            # if layer_params['Run Eq'] is not None:
            #     stack_params['Run Eq'] = layer_params['Run Eq']

            # if layer_params['Raster'] is not None:
            #     stack_params['Raster'] = layer_params['Raster']

            stack_params[layer_params['Layer Code']] = layer_params

        stack_params['#Layers'] = len(stack_params)
        print(stack_params)
        return stack_params


class StructureParamForm(QWidget):

    def __init__(self, stack_form, is_multi):
        super().__init__()

        # Pull in parameters
        self.stackForm = stack_form
        self.isMulti = is_multi

        # Create Form elements
        self.vbox = QVBoxLayout()
        self.equilForm = DepositionStepForm("Target Equilibration", layer_code=0)
        self.title = QLabel("Structure Parameters")
        self.stackRepLine = QLineEdit()
        self.structureParamForm = QFormLayout()

        # Run form setup
        self.init_widget()

    def init_widget(self):
        self.title.setFont(QFont('Arial', 12, QFont.Bold))
        self.structureParamForm.addRow("Stack Repetitions: ", self.stackRepLine)

        self.vbox.addLayout(self.equilForm)
        if self.isMulti:
            self.vbox.addWidget(self.title)
            self.vbox.addLayout(self.structureParamForm)
        self.vbox.addLayout(self.stackForm)

        self.setLayout(self.vbox)

    def return_deposition_params(self):
        equil_params = self.equilForm.return_layer_params()
        dep_params = self.stackForm.return_stack_params()
        if self.isMulti:
            dep_params['# Stacks'] = self.stackRepLine.text()
        else:
            dep_params['# Stacks'] = 1
        dep_params[equil_params['Layer Code']] = equil_params
        print(dep_params)
        return dep_params


class Deposition(QWidget):  # FIXME: Not sure what to subclass here.

    def __init__(self, structure_widget, laser):
        super().__init__()

        # Pull in parameter info and manipulate for other supporting variables
        self.depParams = structure_widget.return_deposition_params()
        self.current_step_param = {}
        self.laser = laser
        self.layerCodes = []
        for key in self.depParams:
            if type(key) is int:
                self.layerCodes.append(key)
        self.layerCodes.sort()
        self.currentLayerIndex = 0
        self.prevStepEnergy = self.depParams[self.layerCodes[0]]['Energy']

        # Create Timers that will be used
        self.laserOnTimer = QTimer()

        print("DepParams = {}".format(self.depParams))
        print("Layer Codes = {}".format(self.layerCodes))

    def run_step(self, layer_code_index):
        self.current_step_param = self.depParams[self.layerCodes[layer_code_index]]
        print("running step: {}".format(self.current_step_param))
        # FIXME: Once the HV energy set function works, adjust energy values: warn between steps
        # if the energy changes as there will be a time/number of pulses where the energy does not
        # match the setting. Will also need a way to get a timer going.. maybe move this to its own
        # function in the future
        # if current_step_param['Energy'] is not self.prevStepEnergy:
        #     self.laser.set_HV_energy(current_step_param['Energy'])

        self.laser.set_reprate(self.current_step_param['Reprate'])
        # noinspection PyNoneFunctionAssignment,PyAttributeOutsideInit
        self.stepTimer = QTimer.singleShot()
        self.stepTimer.timeout.connect(self.end_step)
        print("Created Step Timer: {} ms".format(self.current_step_param['Time'] * 1000))

        self.laserOnTimer.timeout.connect(self.check_laser_pulsing)
        self.laserOnTimer.start(50)
        self.laser.on()
        print("Laser ON sent")

    def check_laser_pulsing(self):
        if self.laser.rd_opmode() == 'OFF,WAIT':
            pass
        elif self.laser.rd_opmode() == 'ON':
            self.stepTimer.start(self.current_step_param['Time'] * 1000)
            self.laserOnTimer.stop()
        else:
            print("Laser not started")

    def end_step(self):
        self.laser.off()
        print("Laser OFF sent")
        if self.currentLayer is not self.layerCodes[-1]:
            self.confirm_next()

    def confirm_next(self):
        confirm_next = QMessageBox.question(self, 'Dep Step {} Complete'
                                            .format(self.layerCodes[self.currentLayerIndex]),
                                            'Press OK to begin next step, make sure shutters,\
                                            targets, etc are placed correctly for dep step {}.'
                                            .format(self.layerCodes[self.currentLayerIndex + 1]),
                                            QMessageBox.Ok |
                                            QMessageBox.Abort,
                                            QMessageBox.Abort)
        if confirm_next == QMessageBox.Ok:
            self.currentLayerIndex += 1
            self.run_step(self.currentLayerIndex)
        elif confirm_next == QMessageBox.Cancel:
            print('Deposition aborted by user')
            pass


class MainWindow(QMainWindow):

    def __init__(self, laser):
        super().__init__()
        self.laser = laser

        # Create a docked widget to hold the LSC module
        self.lscDocked = QDockWidget()
        self.init_ui()

    def init_ui(self):
        self.setObjectName('Main Window')
        self.setWindowTitle('PLD Laser Control')
        self.setCentralWidget(DepControlBox(self.laser))

        self.lscDocked.setWidget(LaserStatusControl(self.laser))
        self.lscDocked.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        self.setCorner(Qt.TopLeftCorner | Qt.TopRightCorner, Qt.TopDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner | Qt.BottomRightCorner, Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.TopDockWidgetArea, self.lscDocked)


def main():
    app = QApplication(sys.argv)
    # Start LaserComm and connect to laser
    # Use the following call for remote testing (without access to the laser), note that the laser.yaml file must be in
    # the working directory
    laser = VisaLaser('ASRL3::INSTR', 'laser.yaml@sim')
    # laser = VisaLaser('ASRLCOM3::INSTR', '@py')

    ex = MainWindow(laser)
    ex.show()

    sys.exit(app.exec_())


# =============================================================================
# Start the GUI (set up for testing for now)
# FIXME: Need to finalize main loop for proper operation
# =============================================================================
if __name__ == '__main__':
    main()
