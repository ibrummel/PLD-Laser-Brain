import os
import numpy as np
import socket
from time import sleep
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap
from src.ui.docked_pyrometer_control_ui import Ui_docked_pyro_controls
from PyQt5.QtWidgets import QDockWidget, QMessageBox, QFileDialog, QMainWindow
from Endurance_Pyrometer import EndurancePyrometer
from datetime import date, datetime


class PyrometerControl(QDockWidget):
    def __init__(self, pyrometer: EndurancePyrometer, parent: QMainWindow):
        """
        A dockable widget made to work with the PLD/laser control GUI developed for the Ihlefeld group PLD system

        :param pyrometer: Provide the instance of the pyrometer class that you wish to read data from for the widget
        """
        # Initialize the super class dock widget
        super(PyrometerControl, self).__init__()

        # Initialize the ui from the python UI file
        self.ui = Ui_docked_pyro_controls()
        self.ui.setupUi(self)
        # Save the pyrometer object to a class variable
        self.pyrometer = pyrometer
        # Set the initial logging state to false (don't start logging on init)
        self._logging = False
        # Check if pyro connected
        self._pyro_connected = False
        self.check_pyro_connection()
        # Read the current slope from the pyrometer and put it in the UI
        self.ui.ln_pyro_slope.setText(str(self.pyrometer.get_slope()))
        #  Set up logging timer.
        self._log_interval = 0.250
        self.ui.ln_log_interval.setText(str(self._log_interval))
        self.log_interval_timer = QTimer()
        # Note: Timer will always run, timeout will only trigger a write to the log if self._logging == True
        self.log_interval_timer.start(1000 * self._log_interval)
        # Set a default value for the pyrometer log file + initialize GUI
        self._log_file = r"./Pyrometer_Logs/{}_pyrometer_log.csv".format(date.today().strftime("%Y.%m.%d"))
        self.ui.ln_pyro_log_file.setText(self._log_file)
        # Set up a timer to continually update the GUI with the current temperature.
        self.pyrometer_value_update_timer = QTimer()
        self.pyrometer_value_update_timer.start(250)  # Update live temperature readout every 0.25 seconds
        # Set up the video frame timer. Timeout should trigger a new video frame. Starting with 12 fps, may increase
        #  depending on performance.
        self._video_fps = 12
        self.video_frame_timer = QTimer()

        self.init_connections()

    def init_connections(self):
        """
        Connect GUI controls to the correct functions

        :return: None
        """
        # Note that connecting the start stop button is handled in the check pyrometer connected routine
        self.ui.ln_pyro_log_file.editingFinished.connect(self.set_log_file_by_line)
        self.ui.btn_pyro_log_file.clicked.connect(self.set_log_file_by_dialog)
        self.ui.ln_log_interval.editingFinished.connect(self.set_log_interval)
        self.ui.ln_pyro_slope.editingFinished.connect(self.set_pyrometer_slope)
        self.ui.btn_get_frame.clicked.connect(self.get_single_frame)
        self.ui.check_enable_video.clicked.connect(self.set_live_video)
        self.video_frame_timer.timeout.connect(self.update_live_image)
        self.pyrometer_value_update_timer.timeout.connect(self.update_pyrometer_values)
        self.log_interval_timer.timeout.connect(self.log_to_file)
        # DONE: Finish connections

    def check_pyro_connection(self):
        """
        Check that the pyrometer is connected.

        :return: None
        """
        prev_state = self._pyro_connected
        try:
            self.pyrometer.get_twocolor_temp()
            self._pyro_connected = not self.pyrometer._pyrometer_timeout
        except socket.timeout as error:  # TODO: Figure out what the actual socket timeout error is called
            self._pyro_connected = not self.pyrometer._pyrometer_timeout
            print("Connection to pyrometer timed out")

        if prev_state != self._pyro_connected:
            if not self._pyro_connected:
                self.ui.btn_pyro_log_start_stop.setText("Check Connection")
                try:
                    self.ui.btn_pyro_log_start_stop.clicked.disconnect(self.start_stop_logging)
                except TypeError:
                    print('Tried to disconnect start_stop_logging but it was not connected')
                self.ui.btn_pyro_log_start_stop.clicked.connect(self.check_pyro_connection)
            elif self._pyro_connected:
                self.ui.btn_pyro_log_start_stop.setText("Start Logging" if not self._logging else "Stop Logging")
                try:
                    self.ui.btn_pyro_log_start_stop.clicked.disconnect(self.check_pyro_connection)
                except TypeError:
                    print('Tried to disconnect check_pyro_connection but it was not connected')
                self.ui.btn_pyro_log_start_stop.clicked.connect(self.start_stop_logging)

        # DONE: Finish logic for checking connected and add actions on log button changing to reconnect button
        # DONE: Add timeout to the _communicate function in Endurance_Pyrometer

    def set_log_interval(self):
        """
        Set the interval for how often to log the temperature to the log file.

        :return: None
        """
        if self._pyro_connected:
            interval = float(self.ui.ln_log_interval.text())
            self.log_interval_timer.setInterval(1000 * interval)
            self.ui.ln_log_interval.setText(str(interval))

    def set_pyrometer_slope(self):
        """
        Set the pyrometer slope from the GUI. Will trigger any time that the value is edited

        :return: None
        """
        if self._pyro_connected:
            self.pyrometer.set_slope(float(self.ui.ln_pyro_slope.text()))
            self.update_pyrometer_values()

    def start_stop_logging(self):
        """
        Start logging the temperature to the supplied temperature log file.

        :return: None
        """
        # DONE: Actually make this do something.
        # Flipping the self._logging flag will cause writes to the log file to begin.
        self._logging = not self._logging
        print("Start stop logging ran. self._logging={}".format(self._logging))
        if self._logging:
            self.log_to_file()
        self.ui.btn_pyro_log_start_stop.setText("Start Logging" if not self._logging else "Stop Logging")

    def check_log_file(self):
        """
        Check the validity of the current value for self._log_file and that it doesn't already exist.

        :return: bool
        """
        if os.path.isfile(self._log_file):
            overwrite = QMessageBox.warning(self, 'File already exists',
                                            'This log file already exists. Would you like to overwrite?',
                                            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
                                            QMessageBox.No)
            if overwrite == QMessageBox.Yes:
                os.remove(self._log_file)
            elif overwrite == QMessageBox.No:
                self.set_log_file_by_dialog()
            elif overwrite == QMessageBox.Cancel:
                return False
        elif self._log_file == os.path.join('~') or self._log_file == '':
            no_file_selected = QMessageBox.warning(self, 'No File Selected',
                                                   'No file has been selected for writing log data, '
                                                   'please pick a file to save to.',
                                                   QMessageBox.Ok | QMessageBox.Cancel,
                                                   QMessageBox.Ok)
            if no_file_selected == QMessageBox.Ok:
                self.set_log_file_by_dialog()
            elif no_file_selected == QMessageBox.Cancel:
                return False

        return True

    def set_log_file_by_dialog(self):
        """
        Set the value for the log file path by using a graphical dialog.

        :return: None
        """
        # Get the file name from a dialog provided by QT framework
        file_name = QFileDialog.getSaveFileName(self,
                                                'Select a file to save data...',
                                                self._log_file,
                                                "CSV Files (*.csv);;All Types (*.*)",
                                                options=QFileDialog.DontConfirmOverwrite)
        # Verify that the file name is valid & not overwriting
        self._log_file = file_name[0]
        self.check_log_file()

        # If the file does not exist & the path you are going to save to doesn't exist, create it.
        if not os.path.exists(os.path.dirname(os.path.abspath(self._log_file))):
            try:
                os.mkdir(os.path.dirname(os.path.abspath(self._log_file)))
            except PermissionError:
                permission_denied = QMessageBox.warning(self, 'Permission Denied',
                                                        'Permission to create the specified folder was denied. \
                                                        Please pick another location to save your data',
                                                        QMessageBox.OK, QMessageBox.Ok)
                if permission_denied == QMessageBox.Ok:
                    return self.set_log_file_by_dialog()

        # Put the updated file name in the UI
        self.ui.ln_pyro_log_file.setText(self._log_file)

    def set_log_file_by_line(self):
        """
        Set the value for the log file path by using the value in the LineEdit for file dialog.

        :return: None
        """
        # Save the old log file to restore if the new file is bad
        old_log_file = self._log_file
        # Set log file based on the value in the line
        self._log_file = self.ui.ln_pyro_log_file.text()
        # Check the new log file and restore the old one if it doesn't pass
        if not self.check_log_file():
            self._log_file = old_log_file

    def log_to_file(self):
        """
        Write the current time, slope, and temperature to the log file if self._logging is set to true.

        :return: None
        """
        if self._logging:
            if not os.path.exists(self._log_file):
                with open(self._log_file, 'w') as log:
                    log.write('Timestamp\tSlope\tTemperature\tUnits\n')
            with open(self._log_file, 'a') as log:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                slope, temp, unit = self.update_pyrometer_values()
                log.write('{}\t{}\t{}\t{}\n'.format(timestamp, slope, temp, unit))

    def update_pyrometer_values(self):
        """
        Reads the temperature, units and slope from the pyrometer and sets the live readout label text accordingly

        :return: Tuple of slope (float), temp (float), and unit (string)
        """
        if self._pyro_connected:
            try:
                temp = self.pyrometer.get_twocolor_temp()
                unit = self.pyrometer.get_temperature_units()
                temp_str = "{} °{}".format(temp, unit)
                self.ui.lbl_current_pyro_temp.setText(temp_str)
                slope = self.pyrometer.get_slope()
                if not self.ui.ln_pyro_slope.hasFocus():  # Prevent the slope value from being set while user is editing
                    self.ui.ln_pyro_slope.setText(str(slope))
                return slope, temp, unit
            except ValueError:
                self.check_pyro_connection()
        return None, None, None

    def set_live_video(self):
        if self._pyro_connected:
            if self.ui.check_enable_video.isChecked():
                self.video_frame_timer.start(int(1000 / self._video_fps))
            elif not self.ui.check_enable_video.isChecked():
                self.video_frame_timer.stop()

    def get_single_frame(self):
        if self._pyro_connected:
            for i in range(0, 4):
                self.pyrometer.get_live_image()
                sleep(1 / 12)
            self.update_live_image()

    def update_live_image(self):
        """
        Render a new frame in the live video view label widget. Size set based on height of label widget under the
        assumption that the height will always be limiting.
        TODO: see if you can break this with resizing

        :return: None
        """
        if self._pyro_connected:
            img = self.pyrometer.get_live_image()
            qt_format_image = QImage(img['image'].data, img['w'], img['h'], img['bytes_per_line'],
                                     QImage.Format_RGB888)
            pixmap_height = self.ui.lbl_pyro_live_video.size().height()
            pixmap_width = np.round(pixmap_height * (16 / 9))
            scaled_qt_format_image = qt_format_image.scaled(pixmap_width, pixmap_height)
            self.ui.lbl_pyro_live_video.setPixmap(QPixmap.fromImage(scaled_qt_format_image))
