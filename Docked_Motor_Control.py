from PyQt5.QtCore import Qt, QRegExp, QEvent, QTimer
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (QCheckBox, QLabel, QLineEdit, QPushButton,
                             QShortcut, QDockWidget, QApplication, QComboBox)
from RPi_Hardware import RPiHardware
from PyQt5 import uic
import Global_Values as Global
import Static_Functions as Static


class MotorControlPanel(QDockWidget):
    def __init__(self, brain: RPiHardware):
        super(MotorControlPanel, self).__init__()

        # Declare brain as RPi interface object
        self.brain = brain

        # Load the ui file and discover all necessary items
        uic.loadUi('./src/ui/docked_motor_control.ui', self)

        self.btns = {widget.objectName().split('btn_')[1]: widget
                     for widget in self.findChildren(QPushButton, QRegExp('btn_*'))}
        self.lines = {widget.objectName().split('line_')[1]: widget
                      for widget in self.findChildren(QLineEdit, QRegExp('line_*'))}
        self.labels = {widget.objectName().split('lbl_')[1]: widget
                       for widget in self.findChildren(QLabel, QRegExp('lbl_*'))}
        self.checks = {widget.objectName().split('check_')[1]: widget
                       for widget in self.findChildren(QCheckBox, QRegExp('check_*'))}
        self.combos = {widget.objectName().split('combo_')[1]: widget
                       for widget in self.findChildren(QComboBox, QRegExp('combo_*'))}

        self.sc_left = QShortcut(QKeySequence(Qt.Key_Left), self)
        self.sc_right = QShortcut(QKeySequence(Qt.Key_Right), self)

        # self.installEventFilter(self)
        # self.hotkey_disable = False

        self.motor_update_timer = QTimer()

        self.init_connections()
        self.update_fields()
        self.update_target_roster()

    def init_connections(self):
        # Set up updating fields on a timer
        self.motor_update_timer.timeout.connect(self.update_fields)
        self.motor_update_timer.start(100)
        QApplication.instance().instrument_settings.settings_applied.connect(self.update_target_roster)

        # Initiate control connections
        self.btns['sub_up'].pressed.connect(self.sub_up)
        self.btns['sub_up'].released.connect(self.sub_halt)
        self.btns['sub_down'].pressed.connect(self.sub_down)
        self.btns['sub_down'].released.connect(self.sub_halt)
        self.lines['sub_position'].returnPressed.connect(self.move_sub_from_line)
        self.lines['sub_speed'].returnPressed.connect(self.set_sub_speed_from_line)
        self.btns['carousel_next'].clicked.connect(self.target_left)
        self.btns['carousel_prev'].clicked.connect(self.target_right)
        self.combos['current_target'].currentIndexChanged.connect(self.move_to_target)
        self.sc_left.activated.connect(self.target_left)
        self.sc_right.activated.connect(self.target_right)
        # FIXME: Probably don't want this implementation of raster?
        self.checks['raster'].stateChanged.connect(self.raster_current_target)
        self.brain.target_changed.connect(lambda: self.check_raster.setChecked(False))
        self.btns['carousel_home'].clicked.connect(self.brain.home_target_carousel)
        self.btns['sub_home'].clicked.connect(self.brain.home_sub)

    def update_target_roster(self):
        self.combos['current_target'].blockSignals(True)
        self.combos['current_target'].clear()
        self.combos['current_target'].addItems(QApplication.instance().instrument_settings.get_target_roster(
            formatlist=['number', 'composition', 'diameter']))
        self.combos['current_target'].blockSignals(False)

    def update_fields(self):
        if not self.combos['current_target'].hasFocus():
            self.combos['current_target'].setCurrentIndex(self.brain.current_target())

        if not self.lines['sub_position'].hasFocus():
            sub_step_position = int(self.brain.arduino.query_motor_parameters('substrate', 'position'))
            sub_position = sub_step_position / Global.SUB_STEPS_PER_MM + Global.SUB_D0
            self.lines['sub_position'].setText(str(sub_position))

        if not self.lines['sub_speed'].hasFocus():
            sub_step_speed = float(self.brain.arduino.query_motor_parameters('substrate', 'max speed'))
            sub_speed = sub_step_speed / Global.SUB_STEPS_PER_MM
            self.lines['sub_speed'].setText(str(sub_speed))

    # def toggle_hotkeys(self):
    #     # Toggle the hotkey disable boolean
    #     self.hotkey_disable = not self.hotkey_disable
    #
    #     # Act on hotkey_disable
    #     self.sc_left.blockSignals(self.hotkey_disable)
    #     self.sc_right.blockSignals(self.hotkey_disable)
    #
    #     if self.hotkey_disable:
    #         self.installEventFilter(self)
    #     elif not self.hotkey_disable:
    #         self.removeEventFilter(self)

    def sub_up(self):
        self.brain.arduino.update_motor_param('sub', 'start', Global.SUB_UP)

    def sub_down(self):
        self.brain.arduino.update_motor_param('sub', 'start', Global.SUB_DOWN)

    def move_sub_from_line(self):
        goal_pos = float(self.lines['sub_position'].text())
        # Prevents the user from sending a value that will be outside the physical limits of the PLD
        if goal_pos > Global.SUB_DMAX:
            goal_pos = Global.SUB_DMAX
        elif goal_pos < Global.SUB_D0:
            goal_pos = Global.SUB_D0
        self.lines['sub_position'].setText(str(goal_pos))
        self.lines['sub_position'].clearFocus()

        self.brain.move_sub_to(goal_pos)

    def sub_halt(self):
        self.brain.arduino.halt_motor('sub')

    def target_right(self):
        goal = (self.brain.current_target() + 1) % 6
        print("Moving to target {}".format(goal))
        self.brain.move_to_target(goal)

    def target_left(self):
        goal = (self.brain.current_target() - 1) % 6
        print("Moving to target {}".format(goal))
        self.brain.move_to_target(goal)

    def move_to_target(self):
        goal = int(self.combos['current_target'].currentIndex())
        print('Moving to target {}'.format(goal))
        self.brain.move_to_target(goal)

    def set_sub_speed_from_line(self):
        self.brain.set_sub_speed(float(self.lines['sub_speed'].text()))
        self.lines['sub_speed'].clearFocus()

    def raster_current_target(self):
        if self.checks['raster'].isChecked():
            find_string = "./target_carousel/target[@ID='{}']/Size".format(self.brain.current_target())
            target_size = float(QApplication.instance().instrument_settings.pld_settings.find(find_string).text)
            raster_steps = Static.calc_raster_steps(target_size)
            self.brain.arduino.update_motor_param('target', 'raster', raster_steps)
        else:
            self.brain.arduino.update_motor_param('target', 'raster', 0)
            print('Raster Off')
