# controller.py

import threading
import time
import requests
import logging

from config import *
from synonims import *

    # ✅  🎙️ 🧹  ⏳ ⚠️ ❌ 🔵 🔴 🔊 ⚠️ Warning 📝  

# You can integrate hardware control (e.g., GPIO pins) by uncommenting
# and implementing the 'LampController' class from prepared 'hardware_control.py' module:
## from hardware_control import LampController

class Lamp:
    def __init__(self, on=False):
        self.lamp_on = on

    def turnOn(self):
        if self.lamp_on:
            return False    # in case lamp is already on
        else:
            self.lamp_on = True
        return True

    def turnOff(self):
        if not self.lamp_on:
            return False    # in case lamp is already off
        else:
            self.lamp_on = False
        return True



class Controller:
    def __init__(self, sip_call):
        """
        Initialize the Controller.

        Args:
            sip_account: Instance of MyAccount from sip_handler to interact with SIP functionalities.
        """
        self.sip_call = sip_call
        # self.current_call = None
        # Initialize hardware interfaces here, e.g., GPIO pins for lamps
        # For example:
        # self.lamp = LampController(pin=17)  # Example GPIO pin
        # For demonstration, we'll use placeholders.
        self.connected = False
        self.lamp = Lamp(False)
        self.question_id = 0
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    def start(self):
        self.connected = True
        self.question_id = 0
        self.message = ""
        time.sleep(0.3)

        if LANGUAGE == "PL":
            response_text = "Witam. Kim jesteś i w jakie sprawie?"
        elif LANGUAGE == "EN":
            response_text = "Hello, how can I help you?"
        else:
            print(" ❌ Controller: ERROR: No language defined")
            return
        self.play_response(response_text)
            

    def onNewCallX(self, call):
        print(f"Controller stores call handler.")
        # self.current_call = call

    def receive_command(self, command):
        """
        Receive and process a command from doorbell.

        Args:
            command (str): The command to process.
        """
        if not self.connected:
            print(f"Controller: Not connected. command:{command}")
            return

        if len(self.message) == 0:
            self.message = command
        else:
            self.message = self.message + " # " + command

        print(f"Controller: ✅ received: '{command}'")
        # Parse the command and decide what action to take
        if LANGUAGE == "PL":
            self.reasoning_pl(command)
        elif LANGUAGE == "EN":
            self.reasoning_en(command)
        else:
            print(" ❌ Controller: ERROR: No language defined")

    def reasoning_pl(self, command):
        command_tokens = set(command.lower().split())  # crude tokenization

        """
        print(f"=== Tokens: {command_tokens}")
        if command_tokens & TURN_ON_SYNS:
            print(f"----- Token: TURN_ON_SYNS")
        if command_tokens & TURN_OFF_SYNS:
            print(f"----- Token: TURN_OFF_SYNS")
        if command_tokens & HANGUP_SYNS:
            print(f"----- Token: HANGUP_SYNS")
        if command_tokens & LIGHT_SYNS:
            print(f"----- Token: LIGHT_SYNS")
        if command_tokens & COURIER_SYNS:
            print(f"----- Token: COURIER_SYNS")
        if command_tokens & PACK_SYNS:
            print(f"----- Token: PACK_SYNS")
        if command_tokens & BRING_SYNS:
            print(f"----- Token: BRING_SYNS")
        if command_tokens & CONFIRM_SYNS:
            print(f"----- Token: CONFIRM_SYNS")
        if command_tokens & GUESTS_SYNS:
            print(f"----- Token: GUESTS_SYNS")
        if command_tokens & ON_SYNS:
            print(f"----- Token: ON_SYNS")
        if command_tokens & VIS1_SYNS:
            print(f"----- Token: VIS1_SYNS")
        if command_tokens & VIS2_SYNS:
            print(f"----- Token: VIS2_SYNS")
        if command_tokens & PARTY_SYNS:
            print(f"----- Token: PARTY_SYNS")
        if command_tokens & VISIT_SYNS:
            print(f"----- Token: VISIT_SYNS")
        if command_tokens & POSTMAN_SYNS:
            print(f"----- Token: POSTMAN_SYNS")
        if command_tokens & LETTER_SYNS:
            print(f"----- Token: LETTER_SYNS")
        """

        # command "zapal światło"
        if (command_tokens & TURN_ON_SYNS and command_tokens & LIGHT_SYNS):
            if self.lamp.turnOn():
                self.doorbell_relay(2)
                self.play_response("Potwierdzam załączenie światła.")
            else:
                self.play_response("Światło jest już załączone.")

        # command "wyłącz światło"
        elif (command_tokens & TURN_OFF_SYNS and command_tokens & LIGHT_SYNS):
            if self.lamp.turnOff():
                self.doorbell_relay(2)
                self.play_response("Potwierdzam wyłączenie światła.")
            else:
                self.play_response("Światło jest już wyłączone.")

        # command "tak"
        elif self.question_id > 0 and command_tokens & CONFIRM_SYNS:

            match self.question_id:
                case 1:
                    self.push_message(self.message + " - kurier zostawił paczkę.")
                    self.open_door("Obiekt monitorowany, informacja przkazana, proszę wejść i zostawić paczkę pod drzwiami.", 6)

        # command "nie"
        elif self.question_id > 0 and command_tokens & NEGATIVE_SYNS:

            match self.question_id:
                case 1:
                    self.push_message(self.message + " - kurier nie zostawił paczki.")
                    self.hangup("Jeżeli nie, to proszę o kontakt na komórkę.", 6)

        # command "przyniosłem paczkę"
        elif command_tokens & BRING_SYNS and command_tokens & PACK_SYNS:
            self.play_response("Czy możesz zostawić paczkę pod drzwiami?")
            self.question_id = 1

        # command "listonosz mam polecony"
        elif command_tokens & POSTMAN_SYNS and command_tokens & LETTER_SYNS:
            self.push_message(self.message + " - listonosz z poleconym.")
            self.open_door("Zaraz ktoś podejdzie, proszę wejść i poczekać.", 4)

        # command "goście na imprezę"
        elif command_tokens & GUESTS_SYNS and command_tokens & ON_SYNS and command_tokens & PARTY_SYNS:
            self.push_message(self.message + " - goście na imprezę.")
            self.open_door("Przyjęcie w ogrodzie, proszę przejść na tył domu, czekamy.", 5)

        # command "my z wizytą"
        elif (command_tokens & VIS1_SYNS or command_tokens & VIS2_SYNS) and command_tokens & VISIT_SYNS:
            self.push_message(self.message + " - ktoś z wizytą.")
            self.open_door("Zapraszam, zaraz ktoś podejdzie.", 3)


        # command "mam do sprzedania"
        elif command_tokens & BRING_SYNS and command_tokens & TO_SYNS and command_tokens & SELL_SYNS:
            self.hangup("Dziękuję, ale nie jestem zainteresowana.", 5)


        # command "koniec"
        elif command_tokens & HANGUP_SYNS:
            self.hangup("Do widzenia.", 3)
        else:

            self.play_response("Przepraszam, proszę mówić wyraźnie, jednym zdaniem.")
        pass




    def reasoning_en(self, command):
        if command.lower() in ["turn on the lamp", "switch on the lamp", "lamp on"]:
            self.handle_lamp_on()
        elif command.lower() in ["turn off the lamp", "switch off the lamp", "lamp off"]:
            self.handle_lamp_off()
        else:
            self.play_response("I'm sorry, I didn't understand that command.")

    def handle_lamp_on(self):
        """
        Handle the command to turn on the lamp.
        """
        print("Controller: Handling command: Turn on the lamp.")
        # Execute the task (e.g., switch on the lamp)
        # self.lamp.turn_on()
        # For demonstration, we'll simulate the task
        #print("Lamp turned on.")  # Replace with actual hardware control

        # Generate and play TTS response
        response_text = "The lamp has been turned on."
        self.play_response(response_text)

    def handle_lamp_off(self):
        """
        Handle the command to turn off the lamp.
        """
        print("Controller: Handling command: Turn off the lamp.")
        # Execute the task (e.g., switch off the lamp)
        # self.lamp.turn_off()
        # For demonstration, we'll simulate the task
        #print("Lamp turned off.")  # Replace with actual hardware control

        # Generate and play TTS response
        response_text = "The lamp has been turned off."
        self.play_response(response_text)

        """
    def handle_unknown_command(self):
        # Handle unknown or unsupported commands.
        print("Controller: Handling unknown command.")
        response_text = "I'm sorry, I didn't understand that command."
        self.play_tts_response(response_text)
        """
    def hangup(self, message, delay):
        self.play_response(message)
        open_thd = threading.Timer(delay, self.delayed_hangup)
        open_thd.start()

    def delayed_hangup(self):
        self.sip_call.hangupCall()


    def open_door(self, message, delay):
        self.play_response(message)
        open_thd = threading.Timer(delay, self.delayed_open_door)
        open_thd.start()

    def delayed_open_door(self):
        self.doorbell_relay(1)
        time.sleep(4)
        self.sip_call.hangupCall()

    def http_doorbell(self, ip, port, scheme, username, password, door_num="1"):
        # Construct the full endpoint. Example:
        #   http://192.168.1.33:1080/fcgi/do?action=OpenDoor&UserName=banana&Password=aku_V21&DoorNum=1
        url = f"{scheme}://{ip}:{port}/fcgi/do"

        # Query parameters per the Akuvox documentation:
        params = {
            "action": "OpenDoor",
            "UserName": username,
            "Password": password,
            "DoorNum": door_num,
        }

        try:
            # For self-signed certs over HTTPS, set verify=False.
            # We'll set verify=True for HTTP -> no SSL anyway, so it's ignored.
            verify_ssl = (scheme == "https")
            response = requests.get(
                url, params=params, timeout=5, verify=verify_ssl
            )

            if response.status_code == 200:
                # print("Door command sent successfully!")
                # print("Response:", response.text)
                return True
            else:
                # print(f"HTTP {response.status_code} Error:", response.text)
                return False
        except requests.RequestException as e:
            print("Error during request:", e)
            return False

    def doorbell_relay(self, relay_no):
        # Akuvox R20A has only 2 relays
        if relay_no in [1, 2]:
            self.http_doorbell(
                ip=VOX_DOMAIN,
                port=VOX_HTTP_PORT,
                scheme="http",
                username=VOX_RELAY_USER,
                password=VOX_RELAY_PASS,
                door_num=str(relay_no)  # "1" = Relay A
            )
        else:
            print(f" ❌ Controller: ERROR: Wrong relay number={relay_no}")
            
    def play_response(self, response_text):
        # Play the TTS response using SIP handler
        if not self.connected:
            print(f"Controller: Not connected. Cant play:{response_text}")
            return
        if self.sip_call:
            self.sip_call.capturePiperText(response_text)
            #print(f"Controller: Play audio for text={response_text}")
            #play_thd = threading.Thread(self.sip_call.play_tts, args=(response_text, ))
            #print(f"Controller: Start playing in thd={play_thd.name}")
            #play_thd.start()

        else:
            print(f"Controller: No active call to play audio.")


    def push_message(self, message):
        url = "https://api.pushover.net/1/messages.json"
        data = {
            "token": PUSH_API_TOKEN,
            "user": PUSH_USER_KEY,
            "message": message
        }
        response = requests.post(url, data=data)
        return response


    def destroy(self):
        # Allow garbage collection to delete this instance
        del self
