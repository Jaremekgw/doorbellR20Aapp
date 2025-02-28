# sip_handler.py

import pjsua2 as pj
import threading
#from tts import generate_tts_wav
from cleanup import cleanup_wav
import time
# from stt import SpeechToText  # Import the STT module
import globals   # Import the globals module
from controller import Controller  # Import Controller if needed
import os
from config import VOSK_MODEL_PATH
from my_logger import logging, logger_thd
# import numpy as np
import wave
import queue

# Create a thread-safe queue for inter-thread communication
event_queue = queue.Queue()

"""
    Na razie nie stosuje logger tylko print
    logging.info(f"Called init: MyAccount() curThd={threading.current_thread().name}")

    logger_thd.info(f"onCallState id={ci.id} role={ci.role} accId={ci.accId}")
    logging.info(f"rUri={ci.remoteUri} state={ci.state}  stateText={ci.stateText} remAudioCount={ci.remAudioCount} remVideoCount={ci.remVideoCount}")

"""

class SIPReceiver:
    def __init__(self, sip_server_ip, sip_user, sip_pass, listen_port=5060):
        self.ep = pj.Endpoint()
        self.ep.libCreate()

        ep_cfg = pj.EpConfig()
        ep_cfg.logConfig.level = 0 # Adjusted log level  [0..5]  default 3
        self.ep.libInit(ep_cfg)

        self.configure_media_codecs(self.ep)    # additional - print info

        transport_cfg = pj.TransportConfig()
        transport_cfg.port = listen_port
        self.transport = self.ep.transportCreate(pj.PJSIP_TRANSPORT_UDP, transport_cfg)
        self.ep.libStart()

        acc_cfg = pj.AccountConfig()
        acc_cfg.idUri = f"sip:{sip_user}@{sip_server_ip}"
        acc_cfg.regConfig.registrarUri = f"sip:{sip_server_ip}"
        acc_cfg.sipConfig.authCreds.append(pj.AuthCredInfo("digest", "*", sip_user, 0, sip_pass))

        # Initialize Controller with the SIP account placeholder; it will be updated later
        #self.controller = Controller(sip_account=None)

        # Create MyAccount with reference to Controller
        self.account = MyAccount()
        self.account.create(acc_cfg)

        # Update the SIP account in Controller
        #self.controller.sip_account = self.account

        # Set the pj_ep reference for thread registration
        globals.pj_ep = self.ep


    def configure_media_codecs(self, ep):
        """Limit PJSUA2 to only supported audio codecs"""
        # Retrieve all available codecs
        audioCodecs = ep.codecEnum2()
        videoCodecs = ep.videoCodecEnum2()  # video will be available after compiling with  --with-openh264

        print("[INFO] Available codecs:")
        for audioC in audioCodecs:
            print(f"Audio  - {audioC.codecId}  - \t{audioC.desc}")
        for videoC in videoCodecs:
            print(f"Video  - {videoC.codecId}")

        # Enable only commonly used codecs
        #allowed_codecs = ["G722/16000/1", "PCMU/8000/1", "PCMA/8000/1"]
    
        #for codec in codecs:
        #    if codec.codecId in allowed_codecs:
        #        ep.codecSetPriority(codec.codecId, 255)  # Highest priority
        #    else:
        #        ep.codecSetPriority(codec.codecId, 0)  # Disable other codecs

        #print("[INFO] Configured supported codecs.")


    def shutdown(self):
        if not globals.pj_ep.libIsThreadRegistered():
            print(f"Shutting down SIP Receiver... thread_name={threading.current_thread().name} Registered ---")
            globals.pj_ep.libRegisterThread("main_shutdown")
        else:
            print(f"Shutting down SIP Receiver... thread_name={threading.current_thread().name}")
        self.ep.libDestroy()


class MyCall(pj.Call):

    def __init__(self, acc, call_id=pj.PJSUA_INVALID_ID):
        super().__init__(acc, call_id)
        print(f" [sip:MyCall] init: ----")
        self.connected = False
        self.hangup_scheduled = False
        self.players = []  # List to hold multiple AudioMediaPlayer instances
        self.tts_text = "Welcome. Your door has been rung."  # Default TTS text
        # self.dynamic_tts_text = "Hello! Someone is at your door."  # Dynamic TTS text
        self.controller = None  # Reference to Controller instance
        self.audio_med = None
        self.audio_active = False

    def setController(self, controller):
        print(f" [sip:MyCall] setController: ---- ??")
        self.controller = controller
        
    def onCallState(self, prm):
        ci = self.getInfo()
        print(f" [sip:MyCall] onCallState state={ci.stateText}")
        if "CONFIRMED" in ci.stateText and not self.connected:
            self.connected = True
            self.controller.start() # self.capturePiperText, self.hangupCall)

        if "DISCONNECTED" in ci.stateText:
            # Clean up all players

            #if globals.stt_app:
            #    print(f"MyCall: 🔴  stop Vosk blocked.")
            #    # globals.stt_app.stop()

            print(f"Clean all players.")
            for player in self.players:
                try:
                    player.stopTransmit(self.getAudioMedia(-1))
                except Exception as e:
                    print(f"Error stopping player: {e}")
            self.players = []

            if self.controller:
                print(f"Destroy controller.")
                self.controller.destroy()
            else:
                print(f"When disconnecting the controller already destroyed.")

            # Unregister call from MyAccount
            #if self.controller and hasattr(self.controller.sip_handler, "calls"):
            #    if ci.id in self.controller.sip_handler.calls:
            #        del self.controller.sip_handler.calls[ci.id]
            #        print(f"[INFO] Removed call ID {ci.id} from active calls.")

            # Allow garbage collection to delete this instance
            print(f"Destroy Call instance.")
            time.sleep(0.5)
            del self

    def onCallMediaState(self, prm):
        print(f" [sip:MyCall] onCallMediaState: ----")
        ci = self.getInfo()
        # Loop through each media stream in the call.
        for i, mi in enumerate(ci.media):
            print(f"[INFO][Call.onCallMediaState] media.type={mi.type} media.status={mi.status}")
            # Check if this media stream is audio.
            if hasattr(mi, 'type') and mi.type == pj.PJMEDIA_TYPE_AUDIO:
                # Check if its status indicates active media.
                if mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                    try:
                        # AudioMedia represents doorbell
                        self.audio_med = self.getAudioMedia(i)

                        # AudDevManager represents PC
                        self.aud_mgr = globals.pj_ep.audDevManager()

                        # it represents PC capture device like microphone (Piper TTS)
                        #self.mic_piper = self.aud_mgr.getCaptureDevMedia()
                        # intstead of capture from microphone play from file
                        #self.player = pj.AudioMediaPlayer()
                        # like: self.player.createPlayer("/tmp/test_mic.wav")

                        # it creates issue, not closes audio port
                        if globals.stt_app:
                             globals.stt_app.set_callback(self.playbackVoskText)
                        #    globals.stt_app.start(self.playbackVoskText)

                        # it represents PC playback device like speaker (vosk STT)
                        self.speaker_vosk = self.aud_mgr.getPlaybackDevMedia()  # like: player_media = self.aud_mgr.getPlaybackDevMedia()

                        #self.mic_piper.startTransmit(self.audio_med)
                        #self.player.startTransmit(self.audio_med)
                        self.audio_med.startTransmit(self.speaker_vosk)         # like: self.player.startTransmit(player_media)

                        # Connect to Vosk - ✅ Now detect & move the sink-input to vosk_stt
                        if globals.pulse_audio:
                            result = globals.pulse_audio.redirect_play_sink_input(globals.pulse_audio.vosk.sink_id)
                            if not result:
                                print("❌ Could not find PJSUA2 stream for vosk in PulseAudio!")
                                return

                        if globals.tts_app:
                            globals.tts_app.start(self.audio_med)
                            # it works, moved to controller
                            #globals.tts_app.speak("You are welcome, please get in the house.")

                        # it works
                        # test_thd = threading.Timer(1, self.delayed_play)
                        # test_thd.start()

                        self.audio_active = True
                        # set timeout for connection
                        hang_thd = threading.Timer(120, self.hangupCall)
                        #print(f"Start delayed hangup (5sec) in thd={hang_thd.name}")
                        hang_thd.start()

                    except Exception as e:
                        print(f"onCallMediaState: Error setting up TTS playback: {e}")

    """     - it works
    def delayed_play(self):
        print(f"---  delayed play started.")
        if globals.tts_app:
            print(f"---  delayed play - call: speak()")
            globals.tts_app.speak("Are you still there?  Please show your face to the camera.")
        else:
            print(f"---  delayed play - No object globals.tts_app.")
    """

    def playbackVoskText(self, text):
        if self.controller:
            self.controller.receive_command(text)
        else:
            print(f"MyCall: ERROR: Not defined controller.")

    def capturePiperText(self, text):
        if globals.tts_app:
            globals.tts_app.speak(text)
        else:
            print(f"MyCall: ERROR: Not defined globals.tts_app.")


    def hangupCall(self):
        #print(f" [sip:MyCall] hangupCall: started. - curThd={threading.current_thread().name}")
        if self.hangup_scheduled:
            print(f"hangupCall alrady scheduled.")
            return

        self.hangup_scheduled = True
        #print(f"MyCall: 🔴 start hangupCall")

        try:
            # Check if pj_ep is set
            if globals.pj_ep is None:
                print(f"[WARNING] Global endpoint is not set. Cannot register thread. - curThd={threading.current_thread().name}")
                return

            if not globals.pj_ep.libIsThreadRegistered():
                # print(f"hangupCall:  libIsThreadRegistered() - NOT - Register -----------------")
                # probably always must be set:
                globals.pj_ep.libRegisterThread("hangupCall")

            # Check if call is already terminated
            ci = self.getInfo()
            #print(f"hangupCall current ci.state={ci.state}")
            if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
                print(f"[WARNING] Attempted to hang up a call that's already disconnected.")
                return

            # PJSIP_ESESSIONTERMINATED

            # Remove reference before hangup to avoid double calls
            #if self.controller and hasattr(self.controller.sip_handler, "calls"):
            #    if ci.id in self.controller.sip_handler.calls:
            #        del self.controller.sip_handler.calls[ci.id]
            #        print(f"[INFO] Removed call ID {ci.id} before hangup.")

            #print(f"hangupCall: Hanging up the call...")

            op = pj.CallOpParam()
            op.statusCode = 200  # Using a valid response code for hangup.
            self.hangup(op)
            #print(f"hangupCall: Call hangup successful.")

        except pj.Error as pj_err:
            print(f"[ERROR] PJSUA2 Error during hangup: {pj_err}")
        except Exception as e:
            print(f"Error: during hangup: {e}")



class MyAccount(pj.Account):
    def __init__(self):
        super().__init__()
        self.calls = {}
        #self.controller = controller
        print(f" [sip:MyAccount] Init: ---- curThd={threading.current_thread().name}")

    def onIncomingCall(self, prm):
        print(f" [sip:MyAccount] onIncomingCall: rdataInfo={prm.rdata.info}  callId={prm.callId}")

        call = MyCall(self, prm.callId)

        # Initialize Controller for this call
        controller = Controller(call)

        # pass Controller handler to Call instance
        call.setController(controller)
        self.calls[prm.callId] = call  # Keep reference.

        if not globals.pj_ep.libIsThreadRegistered():
            print(f"onIncomingCall:  libIsThreadRegistered() - NOT - Register -----------------")
            globals.pj_ep.libRegisterThread("onIncommitCall")

        # Answer the call with 200 OK.
        call_prm = pj.CallOpParam()
        call_prm.statusCode = 200
        call.answer(call_prm)
        print(f"Answered incoming call with ID {prm.callId}. Active calls: {len(self.calls)}")

