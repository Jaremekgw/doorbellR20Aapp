# main.py

import os
import sys
import signal
import time

from sip_handler import SIPReceiver
from pa_virt import PulseAudioVirtualDevices
from vosk_stt import VoskSTT
from piper_tts import PiperTTS
from config import *

import globals

"""
    Program works:
    - pjsua2 for sip connection from doorbell
    - Vosk STT (Stream To Text)
    - Tokenizer for command recognition
    - Piper TTS (Text To Stream)
"""

def main():

    # Create and initialize all objects we need
    globals.pulse_audio = PulseAudioVirtualDevices()
    print("-----------  Init VoskSTT  -------------------")
    vosk_app = VoskSTT(VOSK_MODEL_PATH, globals.pulse_audio)
    print("-----------  Start VoskSTT  -------------------")
    vosk_app.start()  # move to sip_handler after connected (some issue after moving it)
    globals.stt_app = vosk_app
    #print("-----------  Init PiperTTS  -------------------")
    piper_app = PiperTTS(globals.pulse_audio, PIPER_MODEL_PATH)
    #piper_app.start()
    globals.tts_app = piper_app
    print("-----------  Init SIPReceiver  -------------------")
    receiver = SIPReceiver(SIP_DOMAIN, SIP_USER, SIP_PASS, LISTEN_PORT)

    print("SIP Receiver is running. Press Ctrl+C or send SIGTERM to quit.")

    # Single function to shut everything down gracefully
    def do_shutdown():
        # Optional: ensure we only run this once
        if getattr(do_shutdown, "_has_run", False):
            return
        do_shutdown._has_run = True

        print("Shutting down gracefully...")
        # Shut down SIP
        receiver.shutdown()
        # Shut down STT
        vosk_app.stop()
        # Shut down TTS
        #piper_app.stop()
        # Clean up PulseAudio Virtual Devices
        if globals.pulse_audio:
            globals.pulse_audio.cleanup()
            globals.pulse_audio = None

    # Handle signals (SIGINT, SIGTERM) by calling do_shutdown()
    def signal_handler(sig, frame):
        print(f"Received shutdown signal ({sig}). Exiting gracefully...")
        do_shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Main loop
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("Exiting by KeyboardInterrupt...")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Ensure all objects are shut down regardless of how we exit
        do_shutdown()

if __name__ == "__main__":
    main()

