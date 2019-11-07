import sys

from PyQt5 import uic
from PyQt5.QtCore import QTimer, QObject, QRegExp
from PyQt5.QtGui import QFont, QIntValidator, QDoubleValidator, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (QCheckBox, QFileDialog, QLabel, QLineEdit, QVBoxLayout,
                             QWidget, QMessageBox, QFormLayout, QFrame, QPushButton, QListView, QListWidgetItem,
                             QListWidget, QComboBox, QApplication)
import os
import xml.etree.ElementTree as ET
from math import trunc

# ToDo: Write validators for steps

class DepStepItem(QListWidgetItem):

    def __init__(self, *__args, copy_idx=None):
        super().__init__(*__args)

        # Add placeholder step variables to the item
        if type(copy_idx) == int:
            self.set_params(self.parent.item(copy_idx).get_params())
        else:
            self.step_params = {
                'step_index': None,
                'step_name': 'New Step',
                'target': 1,
                'raster': True,
                'tts_distance': 100,
                'num_pulses': 100,
                'reprate': 5,
                'time_on_step': 20,
                'delay': 0
            }

        # self.setDropEnabled(False)

    def get_params(self):
        return self.step_params

    def set_params(self, in_step_params):
        self.step_params = in_step_params

    def set_params_from_xml(self, xml):
        if xml.tag != 'step':
            print('Invalid xml element provided to load step from')
            return
        self.step_params = {
            'step_index': xml.get('step_index'),
            'step_name': xml.get('step_name'),
            'target': xml.find('./target').text,
            'raster': xml.find('./raster').text,
            'tts_distance': xml.find('./tts_distance').text,
            'num_pulses': xml.find('./num_pulses').text,
            'reprate': xml.find('./reprate').text,
            'time_on_step': xml.find('./time_on_step').text,
            'delay': xml.find('./delay').text
        }

    def set_step_index(self, step_index):
        self.step_params['step_index'] = step_index

    def set_step_name(self, name):
        self.step_params['step_name'] = name
        self.setText(name)

    def set_target(self, target):
        self.step_params['target'] = target

    def set_raster(self, raster):
        self.step_params['raster'] = raster

    def calc_time_on_step(self):
        self.step_params['time_on_step'] = int(self.step_params['num_pulses'] / self.step_params['reprate'])

    def set_delay(self, delay):
        self.step_params['delay'] = delay

    def get_xml_element(self, get_subelement_dict=False):
        tags = ['step_name', 'step_index']
        step_xml_root = ET.Element('step')
        step_xml_subelements = {key: ET.SubElement(step_xml_root, key)
                                for key in self.step_params
                                if key not in tags}
        for key in tags:
            step_xml_root.set(key, str(self.step_params[key]))
        for key, element in step_xml_subelements.items():
            element.text = str(self.step_params[key])

        # if requested also return the dict for the subelements to make it easier to manipulate elswhere.
        if get_subelement_dict is True:
            return step_xml_root, step_xml_subelements

        return step_xml_root


class DepControlBox(QWidget):

    def __init__(self):
        super().__init__()
        # ToDo: I will probably need this when I set up the actual running of the deposition. Maybe that should just be
        #  worker class to allow for putting it on another thread... will also need access to the brain and maybe the
        #  arduino directly. Yeah, that makes sense. Shouldn't need this here.
        # self.laser = laser

        # Load ui file and discover controls
        uic.loadUi('./src/ui/pld_deposition_editor.ui', self)

        self.btns = {widget.objectName().split('btn_')[1]: widget
                     for widget in self.findChildren(QPushButton, QRegExp('btn_*'))}
        self.lines = {widget.objectName().split('line_')[1]: widget
                      for widget in self.findChildren(QLineEdit, QRegExp('line_*'))}
        self.labels = {widget.objectName().split('lbl_')[1]: widget
                       for widget in self.findChildren(QLabel, QRegExp('lbl_*'))}
        self.checks = {widget.objectName().split('check_')[1]: widget
                       for widget in self.findChildren(QCheckBox, QRegExp('check_*'))}
        self.checks['raster'].setTristate(False)
        self.combos = {widget.objectName().split('combo_')[1]: widget
                       for widget in self.findChildren(QComboBox, QRegExp('combo_*'))}
        # Set the available list of targets in the combo box
        # Todo: get targets and their locations
        self.update_targets()

        self.list_view = self.findChildren(QListWidget, QRegExp('list_dep_steps'))[0]
        self.list_view.setSelectionMode(QListView.ExtendedSelection)
        # self.list_model = QStandardItemModel(self.list_view)
        # self.list_view.setModel(self.list_model)
        # FIXME: Build in the ability to load from an xml

        # Keep track of step that is currently being edited
        self.current_step_index = None

        self.init_connections()

    def init_connections(self):
        # TODO: Connect everything once supporting functions are written
        self.btns['add_step'].clicked.connect(self.add_deposition_step)
        self.btns['delete_steps'].clicked.connect(self.delete_selected_steps)
        self.btns['copy_step'].clicked.connect(self.copy_deposition_step)
        self.lines['step_name'].editingFinished.connect(self.update_item_name)
        self.btns['run_dep'].clicked.connect(self.run_deposition)
        self.list_view.currentItemChanged.connect(self.on_item_change)

    def on_item_change(self, current, previous):
        # Commit the changes by the user to the previously selected step
        if previous is not None:
            self.commit_changes(previous)
        # Update indices for all items before loading the new item. This will make indices make sense
        self.update_step_indices()
        # Load the values from the new steps into the controls
        self.load_step_params(current)

    def update_step_indices(self):
        for index in range(0, self.list_view.count()):
            self.list_view.item(index).set_step_index(index)

    def update_item_name(self):
        item = self.list_view.currentItem()
        self.commit_changes(item)
        item.setText(item.step_params['step_name'])

    def load_step_params(self, item):
        # Load parameters from the item that is passed in
        ret_params = item.get_params()

        for key, value in ret_params.items():
            ret_params[key] = str(value)

        # Apply parameters to controls
        self.lines['step_name'].setText(item.text())
        self.combos['select_target'].setCurrentText(ret_params['target'])
        self.checks['raster'].setChecked(bool(ret_params['raster']))
        self.lines['tts_distance'].setText(ret_params['tts_distance'])
        self.lines['num_pulses'].setText(ret_params['num_pulses'])
        self.lines['reprate'].setText(ret_params['reprate'])
        self.lines['delay'].setText(ret_params['delay'])

    def commit_changes(self, item):
        step_params = {
            'step_index': self.list_view.row(item),
            'step_name': self.lines['step_name'].text(),
            'target': self.combos['select_target'].currentText(),
            'raster': self.checks['raster'].checkState(),
            'tts_distance': self.lines['tts_distance'].text(),
            'num_pulses': self.lines['num_pulses'].text(),
            'reprate': self.lines['reprate'].text(),
            'time_on_step': str(int(self.lines['num_pulses'].text()) / int(self.lines['reprate'].text())),
            'delay': self.lines['delay'].text()
        }

        item.set_params(step_params)

    def update_targets(self):
        self.combos['select_target'].clear()
        self.combos['select_target'].addItems(['target 1', 'target 2'])
        # self.parent.settings.get_target_roster())
        # Todo: get the non-blank targets from settings window?

    def add_deposition_step(self):
        self.list_view.addItem(DepStepItem('New Step {}'.format(self.list_view.count() + 1), copy_idx=None))
        self.update_step_indices()

    def copy_deposition_step(self):
        for item in self.list_view.selectedItems():
            self.list_view.addItem(DepStepItem(item.text(), copy_idx=item.get_params()['step_index']))
        self.update_step_indices()

    def delete_selected_steps(self):
        print(self.list_view.selectedItems())
        for item in self.list_view.selectedItems():
            # Convoluted way to get the index from the selected item and then remove it, only way that seems to work
            self.list_view.takeItem(self.list_view.indexFromItem(item).row())
        self.update_step_indices()

    def update_time_on_step(self):
        self.commit_changes(self.list_view.currentItem())
        self.list_view.currentItem().calc_time_on_step()
        self.labels['time_on_step'].setText(self.list_view.currentItem().step_params['time_on_step'])

    def get_dep_xml(self):
        dep_xml_root = ET.Element('deposition')
        for index in range(0, self.list_view.count()):
            dep_xml_root.insert(index, self.list_view.item(index).get_xml_element())

        return dep_xml_root

    def load_xml_dep(self, xml: ET.Element):
        steps = xml.findall('./step')
        # Make sure that the list of steps is sorted by index before import
        steps.sort(key=lambda x: x.get('step_index'), reverse=False)
        for step in steps:
            temp = DepStepItem('New Step {}'.format(self.list_view.count() + 1), copy_idx=None)
            temp.set_params_from_xml(step)
            self.list_view.addItem(temp)

    def run_deposition(self):
        # ToDo: Write run deposition for real
        ET.dump(self.get_dep_xml())


app = QApplication(sys.argv)
dep = DepControlBox()
dep.show()
sys.exit(app.exec_())