import os

from PyQt5.QtCore import QRegExp, pyqtSignal
from PyQt5.QtWidgets import QTabWidget, QLineEdit, QPushButton, QToolButton, QGroupBox, QFileDialog
from PyQt5 import uic
import xml.etree.ElementTree as ET

# ToDo: Set up validators to limit settings?
class InstrumentPreferencesDialog(QTabWidget):
    settings_applied = pyqtSignal()

    def __init__(self):
        super().__init__()

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

        # Class variables
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
