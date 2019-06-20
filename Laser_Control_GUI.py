# -*- coding: utf-8 -*-
"""
Created on Mon Mar 11 10:01:53 2019

@author: Ian
"""

from PyQt5.QtCore import Qt, QTimer, QObject
from PyQt5.QtGui import QFont, QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog,
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
                             QWidget, QMessageBox, QFormLayout, QStackedWidget,
                             QFrame, QMainWindow, QDockWidget)
import sys
import os
import pickle
from VISA_Communications import VisaLaser
import time
from math import trunc
from BBB_Hardware import BeagleBoneHardware


def truncate(number, decimals=0):
    # Deprecated with external triggering, everything should be calculated on pulse counts now and times should be
    # rounded for display purposes
    if decimals < 0:
        raise ValueError('Cannot truncate to negative decimals ({})'
                         .format(decimals))
    elif decimals == 0:
        return trunc(number)
    else:
        factor = float(10 ** decimals)
        return trunc(number * factor) / factor

# FIXME: Attempt at making validator behavior more pleasing by reimplementing QLineEdit. Default behavior for now.
# class QLineEdit(QLineEdit):
#
#     def __init__(self, *__args):
#         super().__init__()
#         self.return_validator = None
#         self.returnPressed.connect(self.validate)
#
#     def set_return_validator(self, QValidator):
#         self.return_validator = QValidator
#
#     def validate(self):
#         if self.return_validator is None:
#             pass
#         else:
#             if self.return_validator.validate(self.text(), 0) != QValidator.Acceptable:
#                 self.undo()
#                 warn = QMessageBox.critical(self, "Input Error",
#                                             "You have entered an invalid value for this field. Value will be reset.")


# FIXME: Connect all raster items to respective controls
class LaserStatusControl(QWidget):

    def __init__(self, laser, bbb_brain):
        super().__init__()

        # Set up permissible modes list
        self.inModes = {'EGY NGR': 'Energy', 'HV': 'HV'}
        self.outModes = {'Energy': 'EGY NGR', 'HV': 'HV'}

        # Pull in parameters
        self.laser = laser
        self.brain = bbb_brain

        # Create internal variables and set values
        self.ext_reprate_current = self.laser.rd_reprate()

        # Create widgets and other GUI elements
        self.modeSelLabel = QLabel('Mode: ')
        self.modeSel = QComboBox()

        self.egyLabel = QLabel('Energy: ')
        self.current_egy = self.laser.rd_energy()
        self.egy_val = QLineEdit(self.current_egy)
        self.egy_val.setValidator(QIntValidator(50, 510))

        self.hvLabel = QLabel('HV: ')
        self.current_hv = self.laser.rd_hv()
        self.hv_val = QLineEdit(self.current_hv)
        self.hv_val.setValidator(QDoubleValidator(18, 27, 1))

        self.reprateLabel = QLabel('Reprate: ')
        self.int_reprate_current = self.laser.rd_reprate()
        self.reprate_val = QLineEdit(self.int_reprate_current)
        self.reprate_val.setValidator(QIntValidator(0, 20))  # Laser caps at 50, but >20 needs cooling water

        self.rasterCheck = QCheckBox()
        self.extTriggerCheck = QCheckBox()

        self.checkForm = QFormLayout()
        self.checkForm.addRow('Raster?', self.rasterCheck)
        self.checkForm.addRow('EXT Trig?', self.extTriggerCheck)

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
        self.egy_val.returnPressed.connect(self.set_energy)

        # HV setting box: Displays currently set HV for HV mode. For EGY mode
        # displays the HV set by the laser to match energy setting.
        self.hv_val.returnPressed.connect(self.set_hv)

        # Reprate setting box: Displays current reprate. Will display "EXT" if
        # the laser is set to external triggering
        self.reprate_val.returnPressed.connect(self.set_reprate)

        # Set up check boxes. Default raster to on, and set external trigger check
        # based on current laser configuration
        self.rasterCheck.setChecked(True)
        if self.laser.rd_trigger() == "EXT":
            self.extTriggerCheck.setChecked(True)
        self.extTriggerCheck.stateChanged.connect(self.change_trigger)

        # Start Stop Button
        # self.btnOnOff.setAlignment(Qt.AlignCenter)
        self.btnOnOff.clicked.connect(self.change_on_off)

        # Terminal box for debug
        self.terminal.setPlaceholderText('Enter a command here')
        self.terminal.returnPressed.connect(self.terminal_send)

        # Create a Horizontal Layout to contain the value and setting boxes
        self.hbox.addWidget(self.modeSelLabel)
        self.hbox.addWidget(self.modeSel)
        self.hbox.addWidget(self.egyLabel)
        self.hbox.addWidget(self.egy_val)
        self.hbox.addWidget(self.hvLabel)
        self.hbox.addWidget(self.hv_val)
        self.hbox.addWidget(self.reprateLabel)
        self.hbox.addWidget(self.reprate_val)
        self.hbox.addLayout(self.checkForm)

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
        on_opmodes = ['ON', 'OFF,WAIT']
        if not self.egy_val.hasFocus():
            self.egy_val.setText(self.laser.rd_energy())

        if not self.hv_val.hasFocus():
            self.hv_val.setText(self.laser.rd_hv())

        if not self.reprate_val.hasFocus():
            if self.laser.rd_trigger() == 'INT':
                self.reprate_val.setText(self.laser.rd_reprate())
            elif self.laser.rd_trigger() == 'EXT':
                self.reprate_val.setText(self.ext_reprate_current)

        if self.laser.rd_opmode() in on_opmodes:
            if self.laser.rd_trigger() == 'INT':
                self.btnOnOff.setText('Stop Laser (INT Trigger)')
            elif self.laser.rd_trigger() == 'EXT':
                self.btnOnOff.setText('Stop Laser (EXT Trigger)')
        else:
            self.btnOnOff.setText('Start Laser')

    # Sends the command that was typed into the terminal.
    def terminal_send(self):
        try:
            self.terminal.setText(self.laser.query(self.terminal.text()))
            print("Terminal Command Sent")
        except:
            print("An error occurred on sending terminal command")

    # Sends a command to the laser to change mode. Also sets which parameters
    # are editable from the LSC.
    def change_mode(self, mode):
        self.laser.set_mode(self.outModes[mode])
        if self.outModes[mode] == 'HV':
            self.egy_val.setDisabled(True)
            self.hv_val.setDisabled(False)
        if self.outModes[mode] == 'EGY NGR':
            self.egy_val.setDisabled(False)
            self.hv_val.setDisabled(True)

    def change_trigger(self):
        if self.extTriggerCheck.isChecked():
            self.laser.set_trigger('EXT')
        elif not self.extTriggerCheck.isChecked():
            self.laser.set_trigger('INT')

    def change_on_off(self):
        on_opmodes = ['ON', 'OFF,WAIT']
        # On button press stops the timer that updates the display so that
        # we don't see timeouts on pressing the button to stop/start
        self.updateTimer.stop()
        time.sleep(0.01)

        if self.laser.rd_opmode() in on_opmodes:
            if self.laser.rd_trigger() == 'INT':
                self.laser.off()
            elif self.laser.rd_trigger() == 'EXT':
                self.brain.stop_pulsing()

            self.btnOnOff.setText('Start Laser')

        elif self.laser.rd_opmode() == 'OFF:31':
            self.laser_timeout_handler()

        elif self.laser.rd_opmode() == 'OFF:21':
            # FIXME: Add a countdown timer?
            self.warmup_warn()

        else:
            if self.laser.rd_trigger() == 'EXT':
                self.laser.on()
                print('Sent laser on. Laser Status: {}'.format(self.laser.rd_opmode()))
                self.brain.start_pulsing(self.ext_reprate_current)
                self.btnOnOff.setText('Stop External Trigger')
            elif self.laser.rd_trigger() == 'INT':
                self.laser.on()
                self.btnOnOff.setText('Stop Internal Trigger')

        # Re-enables the updater for the LSC
        time.sleep(0.01)
        self.updateTimer.start(int(1000 / int(self.laser.rd_reprate())))

    def laser_timeout_handler(self):
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

    def warmup_warn(self):
        warmup_clear = QMessageBox.question(self, 'Laser Status: Warm-Up',
                                            "Press retry to check again if the warmup is over, cancel to wait",
                                            QMessageBox.Retry |
                                            QMessageBox.Cancel,
                                            QMessageBox.Retry)
        if warmup_clear == QMessageBox.Ok and self.laser.rd_opmode() == 'OFF:21':
            self.warmup_warn()
        elif warmup_clear == QMessageBox.Ok and not self.laser.rd_opmode() == 'OFF:21':
            notify = QMessageBox.question(self, 'Laser Warmup Complete', 'Laser is ready for use',
                                          QMessageBox.Ok, QMessageBox.Ok)
            if notify == QMessageBox.Ok:
                pass

    # def pause_LSC(self):
    #     self.isLSCUpdating = not self.isLSCUpdating
    #     if self.isLSCUpdating:
    #         self.updateTimer.stop()
    #     elif not self.isLSCUpdating:
    #         self.updateTimer.start(1000 / int(self.laser.rd_reprate()))

    def set_energy(self):
        if 50 <= int(self.egy_val.text()) <= 510:
            self.current_egy = self.egy_val.text()
            self.laser.set_energy(self.current_egy)
        else:
            value_error = QMessageBox.question(self, 'Value Error',
                                               'The energy value entered is not within acceptable limits. Energy value\
                                                will be reset to last good value.',
                                               QMessageBox.Ok, QMessageBox.Ok)
            if value_error == QMessageBox.Ok:
                self.egy_val.setText(self.current_egy)
        self.egy_val.clearFocus()

    def set_hv(self):
        if 18.0 <= float(self.hv_val.text()) <= 27.0:
            self.current_hv = self.hv_val.text()
            self.laser.set_hv(self.current_hv)
        else:
            value_error = QMessageBox.question(self, 'Value Error',
                                               'The HV value entered is not within acceptable limits. HV value will\
                                               be reset to last good value.',
                                               QMessageBox.Ok, QMessageBox.Ok)
            if value_error == QMessageBox.Ok:
                self.hv_val.setText(self.current_hv)
        self.hv_val.clearFocus()

    def set_reprate(self):
        if self.laser.rd_trigger() == 'INT':
            if 1 <= int(self.reprate_val.text()) <= 30:
                self.int_reprate_current = self.reprate_val.text()
                self.laser.set_reprate(self.int_reprate_current)
            else:
                value_error = QMessageBox.question(self, 'Value Error',
                                                   'The repitition rate entered is not within acceptable limits. Repitition\
                                                   rate will be reset to last good value.',
                                                   QMessageBox.Ok, QMessageBox.Ok)
                if value_error == QMessageBox.Ok:
                    self.reprate_val.setText(self.int_reprate_current)
        elif self.laser.rd_trigger() == 'EXT':
            if 1 <= int(self.reprate_val.text()) <= 30:
                self.ext_reprate_current = self.reprate_val.text()
                # FIXME: make sure this is connected to the BBB triggering
            else:
                value_error = QMessageBox.question(self, 'Value Error',
                                                   'The repitition rate entered is not within acceptable limits. Repitition\
                                                   rate will be reset to last good value.',
                                                   QMessageBox.Ok, QMessageBox.Ok)
                if value_error == QMessageBox.Ok:
                    self.reprate_val.setText(self.ext_reprate_current)
        self.reprate_val.clearFocus()


class DepControlBox(QWidget):

    def __init__(self, laser):
        super().__init__()
        self.modeList = ["Standard Deposition",
                         "Super Lattice",
                         "PLID",
                         "Custom",
                         "Equilibration"]
        self.laser = laser
        # Initialize program interaction controls
        self.programModeComboLbl = QLabel("Mode:")
        self.program_mode_combo = QComboBox()
        self.program_mode_combo.addItems(self.modeList)
        self.loadBtn = QPushButton("Load...")
        self.saveBtn = QPushButton("Save...")
        self.runCurrentBtn = QPushButton("Run")
        self.leftCol = QVBoxLayout()
        self.hbox = QHBoxLayout()

        # Connect Buttons to their functions
        self.runCurrentBtn.clicked.connect(self.run_step)
        self.saveBtn.clicked.connect(self.save_parameters)
        # FIXME: Build in the ability to load from a dictionary to the Structure parameter form
        self.loadBtn.clicked.connect(self.load_parameters)

        # Create the stacked widget to hold the currently selected deposition type widgets
        self.dep_forms_stack = QStackedWidget()
        # TODO: Write a custom deposition dictionary builder at some point. The default options will stay hard coded.
        # TODO: Add "custom" to the list of options in the combobox once the custom dep builder is written

        # Create the Standard Deposition Structure Form
        # FIXME: See below
        """ 
        Currently stack dictionaries must have labels of the form L#, not sure how to make the loading 
        function arbitrary without assuming either this or the order of the dictionary entries.
        """

        layer = ["Deposition", 1]
        stack = {"L1": layer}
        self.std_dep_widget = StructureParamForm(stack, False, False)

        # Create Super Lattice Deposition Structure Form
        layer1 = ["Material/Composition 1", 1]
        layer2 = ["Material/Composition 2", 2]
        stack = {"L1": layer1, "L2": layer2}
        self.super_lattice_dep_widget = StructureParamForm(stack, True, False)

        # Create a PLID Deposition Structure Form
        layer = ["Deposition", 1]
        stack = {"L1": layer}
        self.plid_dep_widget = StructureParamForm(stack, False, True)

        # Create a Deposition Structure that only contains and equilibrium step
        stack = {}
        self.equilibration_dep_widget = StructureParamForm(stack, False, False)

        # Create a blank widget to fill the custom widget until a custom widget is built/inserted
        self.custom_dep_widget = QFrame()
        # self.custom_widget_layout = QVBoxLayout()
        # self.custom_dep_widget.setLayout(self.custom_widget_layout)

        # Set up UI elements
        self.init_ui()

    def init_ui(self):
        # Add all elements to the left column that will have program interaction controls
        self.leftCol.insertStretch(1)
        self.leftCol.addWidget(self.programModeComboLbl)
        self.leftCol.addWidget(self.program_mode_combo)
        self.leftCol.addSpacing(50)
        self.leftCol.addWidget(self.loadBtn)
        self.leftCol.addWidget(self.saveBtn)
        self.leftCol.addSpacing(50)
        self.leftCol.addWidget(self.runCurrentBtn)
        self.leftCol.insertStretch(1)

        # Connect the controls to signals/slots
        self.program_mode_combo.currentTextChanged.connect(self.dep_widget_switch)

        # Create a stacked widget that will contain the parameter settings for
        # the program that is loaded/being edited
        self.dep_forms_stack.addWidget(self.std_dep_widget)
        self.dep_forms_stack.addWidget(self.super_lattice_dep_widget)
        self.dep_forms_stack.addWidget(self.plid_dep_widget)
        self.dep_forms_stack.addWidget(self.custom_dep_widget)
        self.dep_forms_stack.addWidget(self.equilibration_dep_widget)
        self.dep_forms_stack.setFrameStyle(QFrame.Panel | QFrame.Sunken)
        self.dep_forms_stack.setLineWidth(2)

        # Create the horizontal layout that will contain the program interaction
        # control column and the parameter setting stack
        self.hbox.addLayout(self.leftCol)
        self.hbox.addWidget(self.dep_forms_stack)
        self.setLayout(self.hbox)

    def dep_widget_switch(self):
        widget = self.program_mode_combo.currentText()
        if widget == "Standard Deposition":
            self.dep_forms_stack.setCurrentWidget(self.std_dep_widget)
        elif widget == "Super Lattice":
            self.dep_forms_stack.setCurrentWidget(self.super_lattice_dep_widget)
        elif widget == "PLID":
            self.dep_forms_stack.setCurrentWidget(self.plid_dep_widget)
        elif widget == "Equilibration":
            self.dep_forms_stack.setCurrentWidget(self.equilibration_dep_widget)
        elif widget == "Custom":
            self.dep_forms_stack.setCurrentWidget(self.custom_dep_widget)

    def save_parameters(self):
        save_name = QFileDialog.getSaveFileName(self, "Save deposition profile...", os.path.expanduser('~'),
                                                "Python Pickle Files (*.p)")
        pickle.dump(self.dep_forms_stack.currentWidget().return_deposition_params(), open(save_name[0], 'wb'))

    def load_parameters(self):
        # Prompt user to find the file to load then save it to load_params
        load_name = QFileDialog.getOpenFileName(self, "Load deposition profile...", os.path.expanduser('~'),
                                                "Python Pickle Files (*.p)")
        load_params = pickle.load(open(load_name[0], 'rb'))

        # Load a new StructureParamForm with passed parameters
        loaded_widget = StructureParamForm({})
        loaded_widget.load_deposition_params(load_params)

        # Remove the custom widget from the stack, set custom widget to the loaded widget, then insert it into the stack
        self.dep_forms_stack.removeWidget(self.custom_dep_widget)
        self.custom_dep_widget = loaded_widget
        self.dep_forms_stack.addWidget(self.custom_dep_widget)

        # self.custom_widget_layout.addWidget(loaded_widget)
        self.dep_forms_stack.setCurrentWidget(self.custom_dep_widget)
        self.program_mode_combo.setCurrentText("Custom")

    def run_step(self):
        deposition = Deposition(self.dep_forms_stack.currentWidget(), self.laser)
        deposition.start()


class DepositionStepForm(QWidget):

    def __init__(self, layer_info_array):
        super().__init__()

        # Pull in parameters as variables
        self.stepTitle = layer_info_array[0] + " Parameters"
        self.layerCode = layer_info_array[1]

        # Set up extra parts needed to create an equilibrium step
        if self.layerCode == 0:
            self.formatStr = "Eq "
            self.runEquilCheck = QCheckBox()
            self.rasterCheck = QCheckBox()

        elif 1 <= self.layerCode <= 3:
            self.formatStr = "L{} ".format(self.layerCode)

        # Initialize controls for all types of deposition step form
        self.reprate_line = QLineEdit()
        self.pulse_count_line = QLineEdit()
        self.dep_time_line = QLineEdit()
        self.energy_line = QLineEdit()
        self.title = QLabel(self.stepTitle)
        self.form = QFormLayout()
        self.vbox = QVBoxLayout()

        # Set masks to control the input to parameter fields
        self.reprate_line.setValidator(QIntValidator(0, 20))  # Laser caps at 50, but >20 needs cooling water
        self.pulse_count_line.setValidator(QIntValidator(0, 9999999))
        self.energy_line.setValidator(QIntValidator(50, 510))
        self.dep_time_line.setValidator(QDoubleValidator(0, 9999999, 1))

        # Connect controls to update functions
        self.reprate_line.editingFinished.connect(self.recalculate_time)
        self.pulse_count_line.editingFinished.connect(self.recalculate_time)
        self.dep_time_line.editingFinished.connect(self.recalculate_pulses)
        self.reprate_line.returnPressed.connect(self.focusNextChild)
        self.pulse_count_line.returnPressed.connect(self.focusNextChild)
        self.dep_time_line.returnPressed.connect(self.focusNextChild)
        self.energy_line.returnPressed.connect(self.focusNextChild)

        self.init_form()

    def init_form(self):

        # Set up the title and form for the main deposition settings
        self.title.setFont(QFont('Arial', 12, QFont.Bold))
        if self.layerCode == 0:
            self.form.addRow("Run Equilibration", self.runEquilCheck)
            self.form.addRow("Raster Target (Applies to all Steps)", self.rasterCheck)
        self.form.addRow("{}Reprate: ".format(self.formatStr),
                         self.reprate_line)
        self.form.addRow("{}Pulses: ".format(self.formatStr),
                         self.pulse_count_line)
        self.form.addRow("{}Time: ".format(self.formatStr),
                         self.dep_time_line)
        self.form.addRow("{}Energy: ".format(self.formatStr),
                         self.energy_line)

        self.vbox.addWidget(self.title)
        self.vbox.addLayout(self.form)
        self.setLayout(self.vbox)

    def recalculate_time(self):
        if self.pulse_count_line.text() != "" and self.reprate_line.text() != "":
            new_time = float(self.pulse_count_line.text()) / float(self.reprate_line.text())
            new_time = round(new_time, 2)
            self.dep_time_line.setText(str(new_time))

    def recalculate_pulses(self):
        if self.reprate_line.text() != "" and self.dep_time_line.text() != "":
            new_pulses = float(self.dep_time_line.text()) * float(self.reprate_line.text())
            new_pulses = trunc(new_pulses)
            self.pulse_count_line.setText(str(new_pulses))

    def return_layer_params(self):
        if self.layerCode == 0:
            return {"Step Code": self.layerCode,
                    "Run Eq": self.runEquilCheck.isChecked(),
                    "Raster": self.rasterCheck.isChecked(),
                    "Reprate": self.reprate_line.text(),
                    "Pulses": self.pulse_count_line.text(),
                    "Time": self.dep_time_line.text(),
                    "Energy": self.energy_line.text()}
        else:
            return {"Step Code": self.layerCode,
                    "Run Eq": None,
                    "Raster": None,
                    "Reprate": self.reprate_line.text(),
                    "Pulses": self.pulse_count_line.text(),
                    "Time": self.dep_time_line.text(),
                    "Energy": self.energy_line.text()}

    def load_layer_params(self, params):
        if params["Step Code"] == 0:
            self.runEquilCheck.setChecked(params["Run Eq"])
            self.rasterCheck.setChecked(params["Raster"])
            self.reprate_line.setText(params["Reprate"])
            self.pulse_count_line.setText(params["Pulses"])
            self.dep_time_line.setText(params["Time"])
            self.energy_line.setText(params["Energy"])
        else:
            self.reprate_line.setText(params["Reprate"])
            self.pulse_count_line.setText(params["Pulses"])
            self.dep_time_line.setText(params["Time"])
            self.energy_line.setText(params["Energy"])


class StackParamForm(QVBoxLayout):

    def __init__(self, layer_dict):  # FIXME: Need another function to build the layer dict
        super().__init__()
        self.layer_dict = layer_dict
        self.layer_widgets = {}
        self.init_widget()

    def init_widget(self):
        # Create dictionary of widgets corresponding to the passed arrays of parameters
        for key in self.layer_dict:
            self.layer_widgets[key] = DepositionStepForm(self.layer_dict[key])

        # Add each widget in the dictionary to the layout
        for key in self.layer_widgets:
            self.addWidget(self.layer_widgets[key])

    def return_stack_params(self):
        stack_params = {}

        for key in self.layer_dict:
            layer_params = self.layer_widgets[key].return_layer_params()
            stack_params[layer_params['Step Code']] = layer_params

        stack_params['#Layers'] = len(stack_params)
        print(stack_params)
        return self.layer_dict, stack_params

    def load_stack_params(self, load_params):
        # Clear out existing widgets before generating the loaded widget
        for widget in self.children():
            self.removeWidget(widget)

        # Overwrite the layer_dict and re initialize the widget with new deposition steps
        self.layer_dict = load_params["Structure Dictionary"]
        self.layer_widgets = {}  # Clear any old widgets to prevent double adding them
        self.init_widget()

        # Step through new widgets and load the passed parameters into them.
        for key in self.layer_widgets:
            layer_code = int(key.split("L")[1])
            self.layer_widgets[key].load_layer_params(load_params[layer_code])


class StructureParamForm(QWidget):

    def __init__(self, stack_dict, is_multi_stack=False, is_interval_dep=False):
        super().__init__()

        # Pull in parameters
        self.stack_form = StackParamForm(stack_dict)
        self.is_multi_stack = is_multi_stack
        self.is_interval_dep = is_interval_dep

        # Create Form elements
        self.vbox = QVBoxLayout()
        self.equil_form = DepositionStepForm(["Target Equilibration", 0])
        self.title = QLabel("Structure Parameters")
        self.stack_rep_line = QLineEdit()
        self.stack_rep_line.setValidator(QIntValidator(1, 1000))  # This is basically just so it has to be a number.
        self.dead_time_line = QLineEdit()
        self.dead_time_line.setValidator(QDoubleValidator(0, 3600, 1))  # ^^ No one should ever use 1 hour dead time
        self.structure_param_form = QFormLayout()

        # Run form setup
        self.init_widget()

    def init_widget(self):
        self.title.setFont(QFont('Arial', 12, QFont.Bold))
        if self.is_multi_stack:
            self.structure_param_form.addRow("Stack Repetitions: ", self.stack_rep_line)
        if self.is_interval_dep:
            self.structure_param_form.addRow("Dead Time Interval: ", self.dead_time_line)

        self.vbox.addWidget(self.equil_form)
        if self.is_multi_stack or self.is_interval_dep:
            self.vbox.addWidget(self.title)
            self.vbox.addLayout(self.structure_param_form)

        self.vbox.addLayout(self.stack_form)

        self.setLayout(self.vbox)

    def return_deposition_params(self):
        equil_params = self.equil_form.return_layer_params()

        # Split the returned tuple
        layer_dict, dep_params = self.stack_form.return_stack_params()
        dep_params[equil_params['Step Code']] = equil_params
        dep_params["Multi Stack"] = self.is_multi_stack
        dep_params["Interval Dep"] = self.is_interval_dep
        if self.is_multi_stack:
            dep_params['#Stacks'] = self.stack_rep_line.text()
        else:
            dep_params['#Stacks'] = 1
        if self.is_interval_dep:
            dep_params['Dead Time'] = self.dead_time_line.text()
        else:
            dep_params['Dead Time'] = 0
        dep_params["Structure Dictionary"] = layer_dict
        print(dep_params)
        return dep_params

    def load_deposition_params(self, load_params):
        # Set internal instance variables for rebuilding the widget
        self.is_multi_stack = load_params["Multi Stack"]
        self.is_interval_dep = load_params["Interval Dep"]

        # Create a black StackParamForm then fill it using the load_stack_params function
        self.stack_form = StackParamForm({})
        self.stack_form.load_stack_params(load_params)

        # Reinitialize the widget to build equilibrium and structure parameter fields
        self.init_widget()

        # Load saved parameters in to the equilibratrion fields
        self.equil_form.load_layer_params(load_params[0])

        # Set values in structure parameter fields
        if self.is_multi_stack:
            self.stack_rep_line.setText(load_params["#Stacks"])
        if self.is_interval_dep:
            self.dead_time_line.setText(load_params["Dead Time"])


class Deposition(QObject):  # FIXME: Not sure what to subclass here.

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

    def __init__(self, laser, brain):
        super().__init__()
        self.laser = laser
        self.brain = brain

        # Create a docked widget to hold the LSC module
        self.lscDocked = QDockWidget()
        self.init_ui()

    def init_ui(self):
        self.setObjectName('Main Window')
        self.setWindowTitle('PLD Laser Control')
        self.setCentralWidget(DepControlBox(self.laser))

        self.lscDocked.setWidget(LaserStatusControl(self.laser, self.brain))
        self.lscDocked.setAllowedAreas(Qt.TopDockWidgetArea | Qt.BottomDockWidgetArea)
        self.setCorner(Qt.TopLeftCorner | Qt.TopRightCorner, Qt.TopDockWidgetArea)
        self.setCorner(Qt.BottomLeftCorner | Qt.BottomRightCorner, Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.TopDockWidgetArea, self.lscDocked)


def main():
    app = QApplication(sys.argv)
    # Start LaserComm and connect to laser
    # Use the following call for remote testing (without access to the laser), note that the laser.yaml file must be in
    # the working directory
    # laser = VisaLaser('ASRL3::INSTR', 'laser.yaml@sim')
    laser = VisaLaser('ASRL/dev/ttyS1::INSTR', '@py')
    bbb_brain = BeagleBoneHardware()

    ex = MainWindow(laser, bbb_brain)
    ex.show()

    sys.exit(app.exec_())


# =============================================================================
# Start the GUI (set up for testing for now)
# FIXME: Need to finalize main loop for proper operation
# =============================================================================
if __name__ == '__main__':
    main()
