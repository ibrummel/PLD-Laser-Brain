import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setup(23, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

def home():
	print('Home switch activated')

GPIO.add_event_detect(23, GPIO.RISING, callback=home, bouncetime=200)

while True:
	pass
