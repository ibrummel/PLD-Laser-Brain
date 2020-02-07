from gpiozero import OutputDevice, Button

# Subclass gpiozero devices to add a device name field for later references
class NamedOutputDevice(OutputDevice):
    def __init__(self, *args, **kwargs):
        try:
            self.dev_name = kwargs.pop('dev_name')
        except KeyError as err:
            self.dev_name = None
        super().__init__(*args, **kwargs)


class NamedButton(Button):
    def __init__(self, *args, **kwargs):
        try:
            self.dev_name = kwargs.pop('dev_name')
        except KeyError as err:
            self.dev_name = None
        super().__init__(*args, **kwargs)