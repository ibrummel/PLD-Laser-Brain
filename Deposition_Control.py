import sys

from PyQt5 import uic
from PyQt5.QtCore import QTimer, QObject, QRegExp, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIntValidator, QDoubleValidator, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (QCheckBox, QFileDialog, QLabel, QLineEdit, QVBoxLayout,
                             QWidget, QMessageBox, QFormLayout, QFrame, QPushButton, QListView, QListWidgetItem,
                             QListWidget, QComboBox, QApplication, QMainWindow)
import os
import xml.etree.ElementTree as ET
from RPi_Hardware import RPiHardware
from Laser_Hardware import CompexLaser
from math import trunc


# ToDo: Write validators for steps
class DepStepItem(QListWidgetItem):

    def __init__(self, *__args, copy_idx=None):
        super().__init__(*__args)

        # Add placeholder step variables to the item
        if type(copy_idx) == int:
            self.set_params(self.parentWidget().item(copy_idx).get_params())
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
                'delay': 0,
                'man_action': ''
            }

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
            'delay': xml.find('./delay').text,
            'man_action': xml.find('./man_action')
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
    stop_deposition = pyqtSignal()

    def __init__(self, laser: CompexLaser, brain: RPiHardware, parent: QMainWindow):
        super().__init__()
        self.setParent(parent)

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
        # FIXME: Build in the ability to load from an xml

        # Create a thread to use for running depositions and move the deposition worker to it.
        self.deposition_thread = QThread()
        self.dep_worker_obj = DepositionWorker(laser, brain)
        self.dep_worker_obj.moveToThread(self.deposition_thread)

        self.init_connections()

    def init_connections(self):
        # TODO: Connect everything once supporting functions are written
        self.btns['add_step'].clicked.connect(self.add_deposition_step)
        self.btns['delete_steps'].clicked.connect(self.delete_selected_steps)
        self.btns['copy_step'].clicked.connect(self.copy_deposition_step)
        self.lines['step_name'].editingFinished.connect(self.update_item_name)
        self.list_view.currentItemChanged.connect(self.on_item_change)

        # Cross thread communications
        self.btns['run_dep'].clicked.connect(self.run_deposition)
        self.dep_worker_obj.deposition_interrupted.connect(self.deposition_thread.quit)
        self.dep_worker_obj.deposition_finished.connect(self.deposition_thread.quit)
        self.stop_deposition.connect(self.dep_worker_obj.halt_dep)
        self.deposition_thread.started.connect(self.dep_worker_obj.start_deposition)

    def on_item_change(self, current, previous):
        # Commit the changes by the user to the previously selected step
        if previous is not None:
            self.commit_changes(previous)
        # Update indices for all items before loading the new item. This will make indices make sense
        self.update_step_indices()
        # Load the values from the new steps into the controls
        if current is not None:
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
        self.lines['man_action'].setText(ret_params['man_action'])

    def commit_changes(self, item):
        try:
            step_params = {
                'step_index': self.list_view.row(item),
                'step_name': self.lines['step_name'].text(),
                'target': self.combos['select_target'].currentText(),
                'raster': self.checks['raster'].checkState(),
                'tts_distance': self.lines['tts_distance'].text(),
                'num_pulses': self.lines['num_pulses'].text(),
                'reprate': self.lines['reprate'].text(),
                'time_on_step': str(int(self.lines['num_pulses'].text()) / int(self.lines['reprate'].text())),
                'delay': self.lines['delay'].text(),
                'man_action': self.lines['man_action'].text()
            }

            item.set_params(step_params)
        except ValueError as err:
            print(err)
            print('Failed to set step parameters for {}, '
                  'please check that all values are valid and try again'.format(item.step_name))

    def update_targets(self):
        self.combos['select_target'].clear()
        self.combos['select_target'].addItems(self.parentWidget().settings.get_target_roster())
        # Todo: get the non-blank targets from settings window?

    def add_deposition_step(self):
        self.list_view.addItem(DepStepItem('New Step {}'.format(self.list_view.count() + 1), copy_idx=None))
        self.update_step_indices()

    def copy_deposition_step(self):
        for item in self.list_view.selectedItems():
            self.list_view.addItem(DepStepItem(item.text(), copy_idx=item.get_params()['step_index']))
        self.update_step_indices()

    def delete_selected_steps(self):
        for item in self.list_view.selectedItems():
            # Convoluted way to get the index from the selected item and then remove it, only way that seems to work
            self.list_view.takeItem(self.list_view.indexFromItem(item).row())
        self.update_step_indices()

    def clear_deposition(self):
        self.list_view.clear()
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
        # FIXME: THIS IS BROKEN, NEED TO FIX check state logic.
        # If the button has not been activated, check it then start the deposition
        if not self.btns['run_dep'].isChecked():
            self.btns['run_dep'].setChecked(True)
            self.btns['run_dep'].setText('Stop Deposition')
            # Get a list of steps and then sort it by index

            self.deposition_thread.start()
        # If the button is checked, uncheck and send the stop signal
        elif self.btns['run_dep'].isChecked():
            self.btns['run_dep'].setChecked(False)
            self.btns['run_dep'].setText('Run Current Deposition')
            self.stop_deposition.emit()

        ET.dump(self.get_dep_xml())


# ToDo: Write run deposition for real
class DepositionWorker(QObject):
    deposition_interrupted = pyqtSignal()
    deposition_finished = pyqtSignal()

    def __init__(self, laser: CompexLaser, brain: RPiHardware):
        super().__init__()

        self.laser = laser
        self.brain = brain

        self.stop = False
        self.prev_tts = None
        self.prev_target = None
        self.curr_step_idx = None
        self.steps = None

        self.init_connections()

    def init_connections(self):
        pass

    def start_deposition(self):
        xml = self.parentWidget().get_dep_xml()
        deposition = xml.getroot()
        steps = deposition.findall('./step')
        steps.sort(key=lambda x: x.get('step_index'), reverse=False)

        self.steps = steps
        if self.curr_step_idx is not None:
            resume = QMessageBox.warning(self, 'Previous Deposition Aborted...',
                                         'The previous deposition was aborted, would you like to resume? Press yes '
                                         'to resume, no to restart from the beginning, and cancel to '
                                         'take no action.',
                                         QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                                         QMessageBox.No)
            if resume == QMessageBox.Yes:
                steps = [x for x in steps if int(x.get('step_index')) >= self.curr_step_idx]
                pass
            elif resume == QMessageBox.No:
                self.curr_step_idx = None
                self.start_deposition(steps)
            elif resume == QMessageBox.Cancel:
                return

        for step in steps:
            self.curr_step_idx = step.get('step_index')

            # Move the target carousel
            if self.prev_target != step.find('./target').text:
                self.brain.move_to_target(int(step.find('./target').text))
            self.prev_target = step.find('./target').text

            # Move the Substrate if necessary
            if self.prev_tts != step.find('./tts_distance'):
                # ToDo: Find a way to convert stepper steps to z translation
                sub_position = int(step.find('./tts_distance'))
                self.brain.sub_position(sub_position)

            # Check that the sub and target positions are achieved. block until it is done
            count = 0
            while (self.brain.targets_running() or self.brain.substrate_running()) and not self.stop:
                count += 1
                # Make sure that the stop signal gets read before the motors come to completion.
                QApplication.processEvents()
                if count % 2 == 0:
                    print('Waiting for motors to finish movement')

            # If stop has been sent, halt all and emit interrupted signal
            if self.stop:
                self.abort_all()
                break

            # Start rastering target, if necessary. Abort if brain and step have mismatched targets
            if bool(step.find('./raster')) and self.brain.current_target == int(step.find('./target')):
                self.brain.raster_current_target()
            elif self.brain.current_target != int(step.find('./target')):
                print('Target setting error')
                self.stop = True
                self.abort_all()

            # Start pulsing
            self.brain.start_pulsing(step.find('./reprate').text, step.find('./num_pulses'))

            # Block until laser is finished
            while self.brain.laser_running() and not self.stop:
                count += 1
                # Make sure that the stop signal gets read before the motors come to completion.
                QApplication.processEvents()
                if count % 10 == 0:
                    print('Laser pulses under way')

            # If stop has been sent, halt all and emit interrupted signal
            if self.stop:
                self.abort_all()
                break

            # If there is a manual action item, pop up a box for the user
            if step.find('./man_action').text != '':
                manual_action = QMessageBox.warning(self, 'Manual action required...',
                                                    'The previous step was flagged as needing manual action. '
                                                    'Please {} before continuing.',
                                                    QMessageBox.Ok | QMessageBox.Abort,
                                                    QMessageBox.Ok)
                if manual_action == QMessageBox.Ok:
                    pass
                elif manual_action == QMessageBox.Abort:
                    self.stop = True

    def abort_all(self):
        self.brain.halt_sub()
        self.brain.halt_target()
        self.brain.stop_pulsing()
        self.deposition_interrupted.emit()

    def halt_dep(self):
        self.stop = True
