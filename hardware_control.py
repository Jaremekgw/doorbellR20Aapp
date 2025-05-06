# hardware_control.py

import RPi.GPIO as GPIO
import time


class LampController:
    def __init__(self, pin):
        """
        Initialize the LampController.

        Args:
            pin (int): GPIO pin number connected to the lamp.
        """
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)  # Ensure lamp is off initially

    def turn_on(self):
        """
        Turn on the lamp.
        """
        GPIO.output(self.pin, GPIO.HIGH)
        print("Lamp has been turned on.")

    def turn_off(self):
        """
        Turn off the lamp.
        """
        GPIO.output(self.pin, GPIO.LOW)
        print("Lamp has been turned off.")

    def cleanup(self):
        """
        Clean up GPIO settings.
        """
        GPIO.cleanup()
