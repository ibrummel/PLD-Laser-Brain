from gpiozero import LED, Button
from time import sleep
import serial

buttons = {"sub_bot": Button(22, pull_up=False), "sub_top": Button(18, pull_up=False)}
hi_pins = [LED(27), LED(23)]
for pin in hi_pins:
    pin.on()
    
arduino = serial.Serial('/dev/ttyACM0', baudrate=115200, timeout=1.5)

def callback(button):
    global direct
    if button == buttons["sub_bot"]:
        send_serial('<s,q,p>')
        print('Bot pressed at position {}'.format(return_serial()))
        send_serial('<s,u,g,40350>')
        direct = 'up'
    elif button == buttons["sub_top"]:
        send_serial('<s,q,p>')
        print('Top pressed at position {}'.format(return_serial()))
        send_serial('<s,u,g,0>')
        direct = 'down'
    sleep(0.05)

def send_serial(command: str):
    arduino.write(command.encode('utf-8'))

def return_serial():
    return arduino.readline().decode('utf-8')

for key, button in buttons.items():
    button.hold_time = 0.05
    button.when_held = callback
    
sleep(1)

print('Setup complete, beginning loop')
send_serial('<s,u,g,40350>')
try:
    while True:
        pass 
except KeyboardInterrupt:
    send_serial('<s,h>')
    print('Cancelled by user')

print("Limit switch test complete")
