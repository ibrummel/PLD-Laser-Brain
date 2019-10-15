import os
import sys

from PyQt5.QtCore import QRegExp
from PyQt5.QtWidgets import QApplication, QTabWidget, QLineEdit, QPushButton, QToolButton, QGroupBox, QFileDialog
from PyQt5 import uic
import xml.etree.ElementTree as ET


class InstrumentPreferencesDialog(QTabWidget):

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
        self.groupboxes = {widget.objectName().split('_')[1]: widget
                           for widget in self.findChildren(QGroupBox, QRegExp("gbox_*"))}
        self.lines_targ_motor = {'_'.join(widget.objectName().split('_')[2:]): widget
                                 for widget in self.findChildren(QLineEdit, QRegExp("line_target_max_*"))}
        self.lines_sub_motor = {'_'.join(widget.objectName().split('_')[2:]): widget
                                for widget in self.findChildren(QLineEdit, QRegExp("line_substrate_max_*"))}
        self.lines_laser = {'_'.join(widget.objectName().split('_')[2:]): widget
                                for widget in self.findChildren(QLineEdit, QRegExp("line_laser_max_*"))}

        # Class variables
        self.settings_file_path = 'settings.xml'
        self.pld_settings = ET.Element
        self.parse_xml_to_settings()

        self.init_connections()
        self.init_fields()

    def init_connections(self):
        for widget in self.btns_apply:
            widget.clicked.connect(self.apply)
        for widget in self.btns_ok:
            widget.clicked.connect(self.ok)
        for widget in self.btns_cancel:
            widget.clicked.connect(self.cancel)

    # noinspection PyTypeChecker
    # To avoid erroneous errors where it thinks XML cant handle xpaths as strings
    def init_fields(self):
        for key, widget in self.lines_carousel_comp:
            widget.setText(self.pld_settings.find("./target_carousel/target[@ID='{}']/Composition".format([key])).text)

        for key, widget in self.lines_carousel_size:
            widget.setText(self.pld_settings.find("./target_carousel/target[@ID='{}']/Size".format([key])).text)

        for key, widget in self.lines_targ_motor:
            widget.setText(self.pld_settings.find("./target/{}".format([key])).text)

        for key, widget in self.lines_sub_motor:
            widget.setText(self.pld_settings.find("./substrate/{}".format([key])).text)

        for key, widget in self.lines_laser:
            widget.setText(self.pld_settings.find("./laser/{}".format([key])).text)

    def open(self):
        self.parse_xml_to_settings(self.settings_file_path)
        self.init_fields()
        self.show()

    # noinspection PyTypeChecker
    # To avoid erroneous errors where it thinks XML cant handle xpaths as strings
    def apply(self):
        for key, widget in self.lines_carousel_comp:
            self.pld_settings.find("./target_carousel/target[@ID='{}']/Composition".format([key])).text = widget.text()

        for key, widget in self.lines_carousel_size:
            self.pld_settings.find("./target_carousel/target[@ID='{}']/Size".format([key])).text = widget.text()

        for key, widget in self.lines_targ_motor:
            self.pld_settings.find("./target/{}".format([key])).text = widget.text()

        for key, widget in self.lines_sub_motor:
            self.pld_settings.find("./substrate/{}".format([key])).text = widget.text()

        for key, widget in self.lines_laser:
            self.pld_settings.find("./laser/{}".format([key])).text = widget.text()

        self.write_settings_to_xml()

    def cancel(self):
        self.hide()

    def ok(self):
        self.apply()
        self.hide()

    def parse_xml_to_settings(self, file: str):
        try:
            parsed = ET.parse(file)
        except FileNotFoundError:
            file_name = QFileDialog.getOpenFileName(self,
                                                    'Select valid settings file...',
                                                    os.getcwd(),
                                                    "xml Files (*.xml)")
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

        # settings = {'carousel': {}, 'target': {}, 'substrate': {}, 'laser': {}}
        #
        # for item in pld.findall('./target_carousel/target'):
        #     item_id = item.get('ID')
        #     settings['carousel'][item_id] = {}
        #     settings['carousel'][item_id]['size'] = item.find('Size').text
        #     settings['carousel'][item_id]['composition'] = item.find('Composition').text
        #
        # for item in pld.findall('./target/'):
        #     settings['target'][item.tag] = item.text
        #
        # for item in pld.findall('./substrate/'):
        #     settings['substrate'][item.tag] = item.text
        #
        # for item in pld.findall('./laser/'):
        #     settings['laser'][item.tag] = item.text

        self.pld_settings = pld


    def write_settings_to_xml(self):
        etree = ET.ElementTree(self.pld_settings)
        self.settings_file_path = 'settings.xml'
        etree.write(self.settings_file_path)


app = QApplication(sys.argv)
window = InstrumentOptionsDialog()
app.exec_()
