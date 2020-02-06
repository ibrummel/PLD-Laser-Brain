from gpiozero import OutputDevice, Button
from time import sleep
import serial
from PyQt5.QtWidgets import QWidget, QApplication, QLabel
from PyQt5.QtCore import Qt, pyqtSignal, QEvent, pyqtSlot
import threading

# Subclass gpiozero devices to add a device name field for later references
class NamedOutputDevice(OutputDevice):
    def __init__(self, *args, **kwargs):
        try:
            self.dev_name = kwargs.pop('dev_name')
        except KeyError as err:
            print("No dev_name supplied, set to none")
            self.dev_name=None
        super().__init__(*args, **kwargs)

class NamedButton(Button):
    def __init__(self, *args, **kwargs):
        try:
            self.dev_name = kwargs.pop('dev_name')
        except KeyError as err:
            print("No dev_name supplied, set to none")
            self.dev_name=None
        super().__init__(*args, **kwargs)

class LimLabel(QLabel):
    btn_pressed = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        hold_time = 0.05
        self.buttons = {"sub_bot": NamedButton(22, pull_up=False, hold_time=hold_time, dev_name='sub_bot'),
                        "sub_top": NamedButton(18, pull_up=False, hold_time=hold_time, dev_name='sub_top')}
        self.hi_pins = [NamedOutputDevice(27), NamedOutputDevice(23)]
        for pin in self.hi_pins:
            pin.on()
        self.arduino = serial.Serial('/dev/ttyACM0', baudrate=115200, timeout=1.5)
        self.direct = 'up'
        self.setText(self.direct)
        
        
        for key, button in self.buttons.items():
            button.when_held = self.callback
        print("Main thread: ", threading.get_ident())
        self.btn_pressed.connect(self.change_dir)
        
    @pyqtSlot()    
    def change_dir(self):
        if self.direct == 'up':
            self.send_serial('<s,u,g,0>')
            self.direct = 'down'
        elif self.direct == 'down':
            self.send_serial('<s,u,g,40350>')
            self.direct = 'up'
        else:
            self.send_serial('<s,h>')
        self.send_serial('<s,q,p>')
        print(self.arduino.readline())
        self.setText(self.direct)
        

    def callback(self, device):
        if device == self.buttons["sub_bot"]:
            print('Bot Pressed')
        elif device == self.buttons["sub_top"]:
            print('Top Pressed')
        print("Device {} thread: ".format(device.dev_name), threading.get_ident())
        self.btn_pressed.emit()
            
    def send_serial(self, command: str):
        self.arduino.write(command.encode('utf-8'))

print('Setup complete, beginning loop')
try:
    app = QApplication([])
    label = LimLabel()
    label.show()
    app.exec_()
    
except KeyboardInterrupt:
    label.send_serial('<s,h>')
    print('Cancelled by user')
    print("Limit switch test complete")



