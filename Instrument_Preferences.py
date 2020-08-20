import os

from PyQt5.QtCore import QRegExp, pyqtSignal, QTimer
from PyQt5.QtWidgets import QTabWidget, QLineEdit, QPushButton, QToolButton, QGroupBox, QFileDialog, QDialog, QWidget, \
    QLabel, QMessageBox, QStackedWidget
from PyQt5 import uic
import xml.etree.ElementTree as ET
from RPi_Hardware import RPiHardware


# ToDo: Set up validators to limit settings?
class InstrumentPreferencesDialog(QTabWidget):
    settings_applied = pyqtSignal()

    def __init__(self):
        super().__init__()

        # This is set later to kludge it past initialization order issues FIXME
        self.brain = None
        # Load the .ui file
        uic.loadUi('./src/ui/pld_settings.ui', self)

        # Create pointers to all relevant objects
        self.lines_carousel_comp = {widget.objectName().split('_')[-1]: widget
                                    for widget in self.findChildren(QLineEdit, QRegExp("line_carousel_composition_*"))}
        self.lines_carousel_size = {widget.objectName().split('_')[-1]: widget
                                    for widget in self.findChildren(QLineEdit, QRegExp("line_carousel_size_*"))}
        self.btns_apply = {widget.objectName().split('_')[-1]: widget
                           for widget in self.findChildren(QPushButton, QRegExp("btn_apply_*"))}
        self.btns_ok = {widget.objectName().split('_')[-1]: widget
                        for widget in self.findChildren(QPushButton, QRegExp("btn_ok_*"))}
        self.btns_cancel = {widget.objectName().split('_')[-1]: widget
                            for widget in self.findChildren(QPushButton, QRegExp("btn_cancel_*"))}
        self.btns_unlock = {widget.objectName().split('_')[1]: widget
                            for widget in self.findChildren(QToolButton, QRegExp("tbtn_*_settings_unlock"))}
        self.groupboxes = {widget.objectName().split('gbox_')[1]: widget
                           for widget in self.findChildren(QGroupBox, QRegExp("gbox_*"))}
        self.lines_targ_motor = {widget.objectName().split('line_target_')[1]: widget
                                 for widget in self.findChildren(QLineEdit, QRegExp("line_target_max_*"))}
        self.lines_sub_motor = {widget.objectName().split('line_substrate_')[1]: widget
                                for widget in self.findChildren(QLineEdit, QRegExp("line_substrate_max_*"))}
        self.lines_laser = {widget.objectName().split('line_laser_')[1]: widget
                            for widget in self.findChildren(QLineEdit, QRegExp("line_laser_max_*"))}
        self.pulse_counters = {widget.objectName().split('_')[3]: widget
                               for widget in self.findChildren(QLineEdit, QRegExp("line_pulse_counter_*"))}
        self.btns_laser_maint = {widget.objectName().split('btn_maint_')[1]: widget
                                 for widget in self.findChildren(QPushButton, QRegExp("btn_maint_*"))}

        # Class variables
        self.maint_timer = QTimer()
        self.maint_window = None
        self.settings_file_path = 'settings.xml'
        self.pld_settings = ET.Element  # Empty element tree, needs to be read in on the next line
        # Errors on reading a settings file are handled within this function.
        self.parse_xml_to_settings(self.settings_file_path)

        self.init_connections()
        self.init_fields()

    def init_connections(self):
        for key, widget in self.btns_apply.items():
            widget.clicked.connect(self.apply)
        for key, widget in self.btns_ok.items():
            widget.clicked.connect(self.ok)
        for key, widget in self.btns_cancel.items():
            widget.clicked.connect(self.cancel)

        self.btns_laser_maint['new_fill'].clicked.connect(self.new_gas_fill)
        self.btns_laser_maint['reset_user_counter'].clicked.connect(self.reset_user_counter)

    # noinspection PyTypeChecker
    # To avoid erroneous errors where it thinks XML cant handle xpaths as strings
    def init_fields(self):
        for key, widget in self.lines_carousel_comp.items():
            widget.setText(self.pld_settings.find("./target_carousel/target[@ID='{}']/Composition".format(key)).text)

        for key, widget in self.lines_carousel_size.items():
            widget.setText(self.pld_settings.find("./target_carousel/target[@ID='{}']/Size".format(key)).text)

        for key, widget in self.lines_targ_motor.items():
            widget.setText(self.pld_settings.find("./target/{}".format(key)).text)

        for key, widget in self.lines_sub_motor.items():
            widget.setText(self.pld_settings.find("./substrate/{}".format(key)).text)

        for key, widget in self.lines_laser.items():
            widget.setText(self.pld_settings.find("./laser/{}".format(key)).text)

        if isinstance(self.brain, RPiHardware):
            self.pulse_counters['user'].setText(str(self.brain.laser.rd_user_counter()))
            self.pulse_counters['total'].setText(str(self.brain.laser.rd_total_counter()))

    def init_hardware(self, brain: RPiHardware):
        self.brain = brain

    def reset_user_counter(self):
        #print("Running reset on user counter")
        self.brain.laser.reset_counter()
        self.init_fields()
        #print("User counter reset complete")

    def new_gas_fill(self):
        self.maint_window = NewGasFillDialog(self.brain, self)

    def open(self):
        self.parse_xml_to_settings(self.settings_file_path)
        self.init_fields()
        self.show()

    # noinspection PyTypeChecker
    # To avoid erroneous errors where it thinks XML cant handle xpaths as strings
    def apply(self):
        for key, widget in self.lines_carousel_comp.items():
            self.pld_settings.find("./target_carousel/target[@ID='{}']/Composition".format(key)).text = widget.text()

        for key, widget in self.lines_carousel_size.items():
            self.pld_settings.find("./target_carousel/target[@ID='{}']/Size".format(key)).text = widget.text()

        for key, widget in self.lines_targ_motor.items():
            self.pld_settings.find("./target/{}".format(key)).text = widget.text()

        for key, widget in self.lines_sub_motor.items():
            self.pld_settings.find("./substrate/{}".format(key)).text = widget.text()

        for key, widget in self.lines_laser.items():
            self.pld_settings.find("./laser/{}".format(key)).text = widget.text()

        self.write_settings_to_xml()
        self.settings_applied.emit()

    def get_target_roster(self, formatlist=None, sep=' - '):
        # Create a list of 6 empty strings
        target_roster = [''] * 6

        if formatlist is None:  # Return a list of target compositions
            for key, widget in self.lines_carousel_comp.items():
                target_roster[int(key)] = str(widget.text())
        elif isinstance(formatlist, list):
            for formatter in formatlist:
                # If the target_roster already has non-blank strings, add a separator
                for i, roster_item in enumerate(target_roster):
                    if roster_item != '':
                        target_roster[i] = roster_item + sep

                # Add the next item based on formatter
                if formatter.lower() in ['c', 'composition']:
                    for key, widget in self.lines_carousel_comp.items():
                        target_roster[int(key)] += str(widget.text())
                elif formatter.lower() in ['n', 'number', 'id']:
                    for key in self.lines_carousel_comp:
                        target_roster[int(key)] += ('#' + str(key))
                elif formatter.lower() in ['s', 'size', 'diameter']:
                    for key, widget in self.lines_carousel_size.items():
                        target_roster[int(key)] += (widget.text() + ' mm')

        return target_roster

    def cancel(self):
        self.hide()

    def ok(self):
        self.apply()
        self.hide()

    def parse_xml_to_settings(self, file: str):
        # Make an initial attempt to parse the xml at the standard location
        # Take provisions to find a new file if the file is missing
        try:
            parsed = ET.parse(file)
        except FileNotFoundError:
            file_name = QFileDialog.getOpenFileName(self,
                                                    'Select valid settings file...',
                                                    os.getcwd(),
                                                    "XML Files (*.xml)")
            self.settings_file_path = file_name[0]
            self.parse_xml_to_settings(self.settings_file_path)

        pld = parsed.getroot()
        # If the parsed xml does not have PLD as the root tag, try again
        if pld.tag != 'PLD':
            file_name = QFileDialog.getOpenFileName(self,
                                                    'Select valid settings file...',
                                                    os.getcwd(),
                                                    "xml Files (*.xml)")
            self.settings_file_path = file_name[0]
            self.parse_xml_to_settings(self.settings_file_path)
        self.pld_settings = pld

        # Actually do something with the parsed file
        # ToDo: Verify this, I just inverted the apply function
        self.init_fields()

    def write_settings_to_xml(self):
        etree = ET.ElementTree(self.pld_settings)
        self.settings_file_path = 'settings.xml'
        etree.write(self.settings_file_path)


class NewGasFillDialog(QDialog):
    def __init__(self, brain: RPiHardware, settings: InstrumentPreferencesDialog):
        super().__init__()
        self.brain = brain
        self.setWindowTitle('Excimer Laser New Gas Fill')
        self.settings = settings

        uic.loadUi('./src/ui/laser_maint_new_fill_dialog.ui', self)

        self.stack = self.findChildren(QStackedWidget, QRegExp("stackedWidget"))[0]
        self.pg_prep = self.findChildren(QWidget, QRegExp("pg_prep"))[0]
        self.line_halogen_filter_ratio = self.findChildren(QLineEdit, QRegExp("line_halogen_filter_ratio"))[0]
        self.btn_continue_fill = self.findChildren(QPushButton, QRegExp("btn_continue_fill"))[0]
        self.btn_cancel_fill = self.findChildren(QPushButton, QRegExp("btn_cancel_fill"))[0]

        self.pg_run = self.findChildren(QWidget, QRegExp("pg_run"))[0]
        self.lbl_fill_status = self.findChildren(QLabel, QRegExp("lbl_fill_status"))[0]
        self.line_laser_status = self.findChildren(QLineEdit, QRegExp("line_laser_status"))[0]
        self.line_tube_press = self.findChildren(QLineEdit, QRegExp("line_tube_press"))[0]
        self.btn_ice_cancel = self.findChildren(QPushButton, QRegExp("btn_ice_cancel"))[0]

        self.init_connections()
        self.update_fields()
        self.exec_()

    def init_connections(self):
        self.btn_cancel_fill.clicked.connect(self.close)
        self.btn_continue_fill.clicked.connect(self.start_new_fill)
        self.btn_ice_cancel.clicked.connect(self.abort)

    def update_fields(self):
        filter_ratio = self.brain.laser.rd_filter_contamination()
        self.line_halogen_filter_ratio.setText(filter_ratio)
        opmode = self.brain.laser.rd_opmode()
        self.line_laser_status.setText(opmode)
        tube_press = self.brain.laser.rd_tube_press()
        self.line_tube_press.setText(tube_press)

        return filter_ratio, opmode, tube_press

    def check_fill_status(self):
        filter_ratio, opmode, tube_press = self.update_fields()
        print("Current tube pressure: ", tube_press)

        if opmode == "NEW FILL":
            self.lbl_fill_status.setText("New fill procedure started")
            print("New fill procedure started")
        elif opmode == "NEW FILL, EVAC":
            self.lbl_fill_status.setText("Evacuating laser tube for new gas fill")
            print("Evacuating laser tube for new gas fill")
        elif opmode == "NEW FILL, WAIT":
            self.lbl_fill_status.setText("Performing new fill leak test")
            print("Performing new fill leak test")
        elif opmode == "NEW FILL, FILL":
            self.lbl_fill_status.setText("Filling laser tube with new gas")
            print("Filling laser tube with new gas")
        elif opmode == "NEW FILL:3":
            self.lbl_fill_status.setText("No gas flow for new fill. You need to restart the procedure")
            print("No gas flow for new fill. You need to restart the procedure")
            no_flow = QMessageBox.warning(self, "No gas flow",
                                          "The laser threw a 'No gas flow' error. Please ensure that all relevant "
                                          "cylinders and valves on the gas panel are open then click OK. (Note: laser "
                                          "will continue filling process as soon as gas flow is detected, clicking ok "
                                          "only closes this warning)",
                                          QMessageBox.Ok, QMessageBox.Ok)
        elif opmode == "OFF" or opmode == "OFF:0":
            self.lbl_fill_status.setText("New gas fill complete")
            print("New gas fill complete")
            complete = QMessageBox.information(self, "New Gas Fill Complete",
                                               "The new gas fill procedure is complete click ok to close this dialog",
                                               QMessageBox.Ok, QMessageBox.Ok)
            self.close()
        elif opmode == "SAFETY FILL":
            print("Safety fill triggered, this is most likely due to a laser tube leak according to the manual.")
        else:
            print(opmode)

    def start_new_fill(self):
        self.stack.setCurrentIndex(1)
        self.settings.maint_timer.timeout.connect(self.check_fill_status)
        self.brain.laser.fill_new()
        self.settings.maint_timer.start(250)

    def abort(self):
        self.brain.laser.off()

    def close(self):
        self.settings.maint_timer.stop()
        try:
            self.settings.maint_timer.timeout.disconnect(self.check_fill_status)
        except TypeError:
            pass
        super().close()