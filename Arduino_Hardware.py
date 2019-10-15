import serial
from PyQt5.QtCore import QObject
from time import sleep


class LaserBrainArduino(QObject):

    def __init__(self, port: str):
        super().__init__()

        self.arduino = serial.Serial(port, baudrate=115200, timeout=1.5)  # Standard port with 8N1 configuration
        self.arduino.open()
        self.serial_read_delay = 0.01
        # FIXME: This is a guess at timing that probably needs adjusting but
        #  isn't relevant till we need more serial ports

        self.valid_axes = {'laser': 'l', 'l': 'l',                      # l is for laser
                           'sub': 's', 'substrate': 's', 's': 's',      # s is for substrate
                           'targ': 't', 'target': 't', 't': 't',        # t is for target
                           'pin write': 'o', 'write': 'o', 'o': 'o',    # o is for (gpi)o
                           'pin read': 'i', 'read': 'i', 'i': 'i',      # i is for (gp)i(o)
                           'serial forward': 'f', 'f': 'f',             # f is for (serial) f(orward)
                           'serial read': 'r', 'r': 'r'}                # r is for serial r(ead)

        self.valid_laser_params = {'reprate': 'r', 'r': 'r',
                                   'goal': 'g', 'g': 'g',
                                   'start': 'd', 'd': 'd'}

        self.valid_laser_queries = {'pulses': 'p', 'p': 'p',
                                    'max reprate': 'm', 'm': 'm',
                                    'reprate': 'v', 'r': 'v',
                                    'goal pulses': 'g', 'g': 'g',
                                    'pulses remaining': 'd', 'd': 'd',
                                    'is running': 'r', 'r': 'r'}

        self.valid_motor_params = {'accel': 'a', 'acceleration': 'a', 'a': 'a',
                                   'max speed': 'm', 'm': 'm',
                                   'speed': 'v', 'velocity': 'v', 'v': 'v',
                                   'goal': 'g', 'g': 'g',
                                   'start': 'd', 'manual': 'd', 'd': 'd',
                                   'raster': 'r', 'r': 'r',
                                   'position': 'p', 'p': 'p'}

        self.valid_motor_queries = {'position': 'p', 'p': 'p',
                                    'max speed': 'm', 'm': 'm',
                                    'speed': 'v', 'velocity': 'v', 'v': 'v',
                                    'goal position': 'g', 'g': 'g',
                                    'distance to go': 'd', 'd': 'd',
                                    'is running': 'r', 'r': 'r'}

        self.valid_motors = {'sub': 's', 'substrate': 's', 's': 's',
                             'targ': 't', 'target': 't', 't': 't'}

        self.valid_gpio_status = {'HIGH': 'w', 'high': 'w','High': 'w', 1: 'w', 'w': 'w',
                                  'LOW': 'c', 'low': 'c', 'Low': 'c', 0: 'c', 'c': 'c'}

        # Pins not in use: 'A0': 14, 'A1': 15, 'A7': 21
        self.valid_pin_numbers = {'D2': 2, 'GPIO_HV1': 2, 'D3': 3, 'GPIO_HV2': 3,
                                  'D4': 4, 'GPIO_HV3': 4, 'D5': 5, 'GPIO_HV4': 5,
                                  'D6': 6, 'GPIO_HV6': 6, 'D7': 7, 'GPIO_HV7': 7,
                                  'D8': 8, 'GPIO_HV8': 8, 'D9': 9, 'GPIO_HV9': 9,
                                  'D10': 10, 'BNC1': 10, 'D11': 11, 'BNC2': 11,
                                  'D12': 12, 'BNC3': 12, 'A2': 16, 'BNC4': 16,
                                  'A3': 17, 'BNC5': 17, 'A4': 18, 'PiGPIO21': 18,
                                  'A5': 19, 'PiGPIO20': 19, 'A6': 20, 'PiGPIO19': 20,
                                  'LED': 13}

    def send_serial(self, command: str):
        self.arduino.write(command.encode('utf-8'))

    def return_serial(self):
        return self.arduino.readline().decode('utf-8')

    def update_laser_param(self, command_param, value='null'):
        try:
            command_param = self.valid_laser_params[command_param]
            self.send_serial('<l,u,{},{}>'.format(command_param, value))
        except KeyError:
            print('Invalid laser parameter supplied:', command_param)

    def query_laser_parameters(self, query_param):
        try:
            query_param = self.valid_laser_queries[query_param]
            self.send_serial('<l,q,{}>'.format(query_param))
            return self.return_serial()
        except KeyError:
            print('Invalid laser parameter to query:', query_param)

    def halt_laser(self):
        self.send_serial('<l,h>')

    def update_motor_param(self, motor: str, command_param: str, value='null'):
        try:
            motor = self.valid_motors[motor]
            command_param = self.valid_motor_params[command_param]
            self.send_serial('<{},u,{},{}>'.format(motor, command_param, value))
        except KeyError:
            print('Invalid motor or parameter to update: motor={}, query={}'.format(motor, command_param))

    def query_motor_parameters(self, motor: str, query_param: str):
        try:
            motor = self.valid_motors[motor]
            query_param = self.valid_motor_queries[query_param]
            self.send_serial('<{},q,{}>'.format(motor, query_param))
            return self.return_serial()
        except KeyError:
            print('Invalid motor or parameter to query: motor={}, query={}'.format(motor, query_param))

    def halt_motor(self, motor: str):
        try:
            motor = self.valid_motors[motor]
            self.send_serial('<{},h>'.format(motor))
        except KeyError:
            print('Invalid motor to halt, stopping both motors as a precaution.')
            self.send_serial('<s,h><t,h>')

    def send_pin_status(self, pin_number, status):
        try:
            if type(pin_number) != int:
                pin_number = self.valid_pin_numbers[pin_number]
            status = self.valid_gpio_status[status]
            self.send_serial('<o,{},{}>'.format(pin_number, status))
        except KeyError:
            print('Invalid pin or pin status supplied: pin={}, pin status={}'.format(pin_number, status))

    def read_pin_status(self, pin_number):
        try:
            if type(pin_number) != int:
                pin_number = self.valid_pin_numbers[pin_number]
            self.send_serial('<i,{}>'.format(pin_number))
            return self.return_serial()
        except KeyError:
            print('Invalid pin number supplied: {}'.format(pin_number))

    def serial_forward(self, message: str):
        print('Serial forward not currently implemented')
        # self.send_serial('<f,{}>'.format(message))

    def read_serial_forward(self):
        print('Serial forward not currently implemented')
        # self.send_serial('<r>')
        # sleep(self.serial_read_delay)
        # return self.return_serial()
