import RPi.GPIO as GPIO
from time import sleep

GPIO.setmode(GPIO.BCM)
  
in_pins = {"sub_bottom": 22, "sub_top": 18}
hi_pins = {"sub_bottom_hi": 23, "sub_top_hi": 27}

def test_top():
    while GPIO.input(in_pins['sub_top']):
        pass
    print("Sub top switch pressed")
    
def test_bot():
    while GPIO.input(in_pins['sub_bottom']):
        pass

    print("Sub bottom switch pressed")
    
for pin in hi_pins:
    GPIO.setup(hi_pins[pin], GPIO.OUT, initial=GPIO.HIGH)
    
for pin in in_pins:
    GPIO.setup(in_pins[pin], GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

sleep(1)

try:
    while True:
        if GPIO.input(in_pins['sub_top']) and GPIO.input(in_pins['sub_bottom']):
            print('both')
            sleep(0.2)
        elif GPIO.input(in_pins['sub_top']):
            print('top')
            sleep(0.2)
        elif GPIO.input(in_pins['sub_bottom']):
            print('bottom')
            sleep(0.2)
            
except KeyboardInterrupt:
    print('Cancelled by user')


print("Limit switch test complete")

GPIO.cleanup()