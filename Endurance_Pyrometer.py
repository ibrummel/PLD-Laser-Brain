import socket
import cv2
from time import sleep


class EndurancePyrometer(object):
    def __init__(self, *args, ip_addr="192.168.42.132", port=6363, **kwargs):
        """
        Class for use in controlling and reading values from a Fluke Endurance Pyrometer from a software interface

        :param args: Arguments to be passed to the object init function
        :param ip_addr: The ip address of the pyrometer.
        :type ip_addr: str
        :param port: The port for communication with the pyrometer
        :type port: int
        :param kwargs: Keyword arguments to be passed to the obect init function
        """
        super(EndurancePyrometer, self).__init__(*args, **kwargs)
        # Create an object for connecting to and communicating with the pyrometer
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.ip_addr = ip_addr
        self.port = port
        self.set_webserver_status(1)
        self.set_video_status(1)
        sleep(1)
        self.video_capture = cv2.VideoCapture("{}/camera?action=stream&resolution=720p".format(self.ip_addr))
        self._default_encoding = 'utf-8'
        self._read_length = 1024 * 3
        self._response_char = '!'
        self._error_char = '*'
        self._query_char = '?'
        self._send_termination = '\r'
        self._recv_termination = '\r\n'
        self._valid_param_strings = ['$',
                                     '?',
                                     'B',
                                     'BS',
                                     'D',
                                     'DF',
                                     'DHCP',
                                     'E',
                                     'EC',
                                     'F',
                                     'G',
                                     'GW',
                                     'H',
                                     'I',
                                     'IP',
                                     'J',
                                     'K',
                                     'L',
                                     'M',
                                     'MAC',
                                     'N',
                                     'NM',
                                     'O',
                                     'P',
                                     'PORT',
                                     'Q',
                                     'R',
                                     'RC',
                                     'RX',
                                     'RY',
                                     'S',
                                     'STT',
                                     'T',
                                     'TR',
                                     'TTI',
                                     'U',
                                     'V',
                                     'W',
                                     'WS',
                                     'X$',
                                     'XA',
                                     'XB',
                                     'XD',
                                     'XF',
                                     'XG',
                                     'XH',
                                     'XI',
                                     'XL',
                                     'XM',
                                     'XO',
                                     'XR',
                                     'XRA',
                                     'XS',
                                     'XT',
                                     'XU',
                                     'XV',
                                     'Y',
                                     'Z',
                                     ]

    def _query_param(self, param):
        """
        Helper function to allow easy querying of parameters. Should not be called directly by users, instead should be
        called by functions set up for each parameter of interest.

        :param param: Param string as defined in the Endurance Pyrometer programming guide.
        :type param: str

        :return: String representation of value returned from the pyrometer

        :raises: ValueError
        """
        if param in self._valid_param_strings:
            request = '{}{}{}'.format(self._query_char, param, self._send_termination)
        else:
            raise ValueError("Invalid param string supplied: {}.".format(param))

        answer = self._communicate(request, param)
        return answer

    def _set_param(self, param, value):
        """
        Helper function to allow easy setting of parameters. Should not be called directly by users, instead should be
        called by functions set up for each parameter of interest.

        :param param: Param string as defined in the Endurance Pyrometer programming guide.
        :type param: str
        :param value: Value to set for provided parameter. Will generally be an integer or string as determined in the
                      Endurance pyrometer programming guide
        :type value: str, int

        :return: True on success of setting parameter. False otherwise.

        :raises: ValueError
        """
        if param in self._valid_param_strings:
            request = '{}={}{}'.format(param, value, self._send_termination)
        else:
            raise ValueError("Invalid param string supplied: {}.".format(param))
        answer = self._communicate(request, param)
        if answer == str(value):
            return True
        else:
            return False

    def _communicate(self, request, param):
        """
        Generalized communication with the Endurance Pyrometer via a TCPIP socket.

        :param request: Request string to send to the pyrometer
        :type request: str
        :param param: Parameter of interest to allow stripping of extraneous response characters.
        :type param: str

        :return: Returns value from the pyrometer as a string, to be processed by the calling function
        :rtype: str
        """
        self.socket.settimeout(0.5)
        self.socket.connect((self.ip_addr, self.port))
        self.socket.send(request.encode(self._default_encoding))
        answer = self.socket.recv(self._read_length).decode('utf-8')
        if answer.startswith(self._response_char):
            answer = answer.strip(self._recv_termination + self._response_char + param)
        else:
            answer = None

        self.socket.close()
        return answer

    def get_twocolor_temp(self):
        """
        Get the two-color temperature from the pyrometer.

        :return: Returns a string representing the two-color temperature from the pyrometer
        :rtype: float
        """
        param = "T"
        return float(self._query_param(param))

    def set_temperature_units(self, unit):
        """
        Set the units in firmware for returned temperature from the pyrometer

        :param unit: Provide a string representing the desired unit: C(elsius) or F(ahrenheit)
        :type unit: str

        :returns: Returns true if setting was successful, false on failure
        :rtype bool
        """
        param = "U"
        return self._set_param(param, unit)

    def get_temperature_units(self):
        """
        Get the units set in the pyrometer firmware for reading temperatures

        :return: String representing the currently set units: C(elsius) or F(ahrenheit)
        """
        param = "U"
        return self._query_param(param)

    def set_slope(self, slope):
        """
        Set the slope used to measure temperature.

        :param slope: Two color slope value
        :type slope: float
        """
        param = "S"
        return self._set_param(param, slope)

    def get_slope(self):
        """
        Get the slope from the pyrometer.

        :return: Returns float representing the current slope value from the pyrometer
        :rtype: float
        """
        param = "S"
        return float(self._query_param(param))

    def set_webserver_status(self, onoff):
        """
        Set Endurance Webserver Status

        :param onoff: Set webserver status, 0 sets webserver off, 1 sets webserver on
        :type onoff: int

        :returns: Returns true if setting was successful, false on failure
        :rtype bool
        """
        param = "WS"
        return self._set_param(param, onoff)

    def get_webserver_status(self):
        """
        Get Endurance Webserver Status

        :returns: Returns webserver status. 0 indicates webserver off, 1 indicates webserver on
        :rtype int
        """
        param = "WS"
        return int(self._query_param(param))

    def set_video_status(self, onoff):
        """
        Set Endurance Video Output Status

        :param onoff: Set video output status, 0 sets video off, 1 sets video on
        :type onoff: int

        :returns: Returns true if setting was successful, false on failure
        :rtype bool
        """
        param = "XL"
        return self._set_param(param, onoff)

    def get_video_status(self):
        """
        Get Endurance Video Output Status

        :returns: Returns video output status. 0 indicates video off, 1 indicates video on
        :rtype: int
        """
        param = "XL"
        return int(self._query_param(param))

    def get_live_image(self):
        """
        Capture an image from the live stream off of the Endurance Pyrometer and return it in a useable format.

        :returns: Returns a dictionary with the captured image + statistics
        :rtype: dict
        """
        ret, frame = self.video_capture.read()
        if ret:
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            w, h, ch = rgb_image.shape()
            bytes_per_line = w * ch
            return {'image': rgb_image, 'w': w, 'h': h, 'ch': ch, 'bytes_per_line': bytes_per_line}
        else:
            print("Failed to get image, trying again")
            return self.get_live_image()
