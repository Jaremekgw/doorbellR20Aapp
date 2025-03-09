# main.py

import sys
import signal
import time
import multiprocessing

from sip_handler import SIPReceiver
from pa_virt import PulseAudioVirtualDevices
from vosk_stt import VoskSTT
from piper_tts import PiperTTS
from config import *

import globals

"""
    Following parts are used:
    - main_face.py for Face Recognition
    - pjsua2 for sip connection from doorbell
    - Vosk STT (Stream To Text)
    - Tokenizer for command recognition
    - Piper TTS (Text To Stream)
"""

def main():
    # Create a multiprocessing Event sip connection for face recognition control
    sip_event_connected = multiprocessing.Event()
    sip_event_connected.clear()

    print("-----------  Init Face Recognition  -------------------")
    # Start `main_face.py` as a separate process
    print("🚀 Starting Face Recognition Process...")
    face_recognition_process = multiprocessing.Process(target=start_face_recognition_process, args=(sip_event_connected,))
    face_recognition_process.start()

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
    receiver = SIPReceiver(sip_event_connected, SIP_DOMAIN, SIP_USER, SIP_PASS, LISTEN_PORT)

    print("SIP Receiver is running. Press Ctrl+C or send SIGTERM to quit.")

    # Single function to shut everything down gracefully
    def do_shutdown():
        # Optional: ensure we only run this once
        if getattr(do_shutdown, "_has_run", False):
            return
        do_shutdown._has_run = True

        print("Shutting down gracefully...")

        # Disable face recognition
        sip_event_connected.clear()
        time.sleep(1)  # Give time for shutdown

        # Terminate the face recognition process
        face_recognition_process.terminate()
        face_recognition_process.join()

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

def start_face_recognition_process(multiprocess_event):
    """
    Starts `main_face.py` as a separate process.
    """
    from main_face import main

    main(multiprocess_event)

if __name__ == "__main__":
    main()

