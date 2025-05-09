# sip_handler.py

import pjsua2 as pj
import threading
import time
import queue
import globals   # Import the globals module

from cleanup import cleanup_wav
from controller import Controller  # Import Controller if needed
from config import VOSK_MODEL_PATH
from my_logger import logging, logger_thd
from logger_config import get_logger

# Create a thread-safe queue for inter-thread communication
event_queue = queue.Queue()

"""
    For the beginning I don't use logger, only print
    logging.info(f"Called init: MyAccount() curThd={threading.current_thread().name}")

    logger_thd.info(f"onCallState id={ci.id} role={ci.role} accId={ci.accId}")
    logging.info(f"rUri={ci.remoteUri} state={ci.state}  stateText={ci.stateText} remAudioCount={ci.remAudioCount} remVideoCount={ci.remVideoCount}")

"""

logger = get_logger(__name__)


class SIPReceiver:
    def __init__(self, sip_event_connected, sip_server_ip, sip_user, sip_pass, listen_port=5060):
        self.ep = pj.Endpoint()
        self.ep.libCreate()

        ep_cfg = pj.EpConfig()
        ep_cfg.logConfig.level = 0  # Adjusted log level  [0..5]  default 3
        self.ep.libInit(ep_cfg)

        self.configure_media_codecs(self.ep)    # additional - print info

        transport_cfg = pj.TransportConfig()
        transport_cfg.port = listen_port
        self.transport = self.ep.transportCreate(
            pj.PJSIP_TRANSPORT_UDP, transport_cfg)
        self.ep.libStart()

        acc_cfg = pj.AccountConfig()
        acc_cfg.idUri = f"sip:{sip_user}@{sip_server_ip}"
        acc_cfg.regConfig.registrarUri = f"sip:{sip_server_ip}"
        acc_cfg.sipConfig.authCreds.append(
            pj.AuthCredInfo("digest", "*", sip_user, 0, sip_pass))

        # Create MyAccount
        self.account = MyAccount(sip_event_connected)
        self.account.create(acc_cfg)

        # Set the pj_ep reference for thread registration
        globals.pj_ep = self.ep

    def configure_media_codecs(self, ep):
        """Limit PJSUA2 to only supported audio codecs"""
        # Retrieve all available codecs
        audioCodecs = ep.codecEnum2()
        # video will be available after compiling with  --with-openh264
        videoCodecs = ep.videoCodecEnum2()

        logger.info("Available codecs:")
        for audioC in audioCodecs:
            logger.info(f"Audio  - {audioC.codecId}  - \t{audioC.desc}")
        for videoC in videoCodecs:
            logger.info(f"Video  - {videoC.codecId}")

        # Enable only commonly used codecs
        # allowed_codecs = ["G722/16000/1", "PCMU/8000/1", "PCMA/8000/1"]

        # for codec in codecs:
        #    if codec.codecId in allowed_codecs:
        #        ep.codecSetPriority(codec.codecId, 255)  # Highest priority
        #    else:
        #        ep.codecSetPriority(codec.codecId, 0)  # Disable other codecs

        # logger.info("Configured supported codecs.")

    def shutdown(self):
        if not globals.pj_ep.libIsThreadRegistered():
            logger.info(
                f"Shutting down SIP Receiver... thread_name={threading.current_thread().name} Registered ---")
            globals.pj_ep.libRegisterThread("main_shutdown")
        else:
            logger.info(
                f"Shutting down SIP Receiver... thread_name={threading.current_thread().name}")
        self.ep.libDestroy()


class MyCall(pj.Call):

    def __init__(self, event_connected, acc, call_id=pj.PJSUA_INVALID_ID):
        super().__init__(acc, call_id)
        self.connected = False
        self.event_connected = event_connected
        self.hangup_scheduled = False
        self.players = []  # List to hold multiple AudioMediaPlayer instances
        self.controller = None  # Reference to Controller instance
        self.audio_med = None
        self.audio_active = False

    def setController(self, controller):
        self.controller = controller

    def onCallState(self, prm):
        ci = self.getInfo()
        logger.info(f" [sip:MyCall] onCallState state={ci.stateText}")
        if "CONFIRMED" in ci.stateText and not self.connected:
            self.connected = True
            self.controller.start()  # self.capturePiperText, self.hangupCall)

        if "DISCONNECTED" in ci.stateText:
            # Clean up all players

            # if globals.stt_app:
            #    logger.info(f"MyCall: 🔴  stop Vosk blocked.")
            #    # globals.stt_app.stop()

            # object has no attribute 'event_connected'
            self.event_connected.clear()

            logger.info(f"Clean all players.")
            for player in self.players:
                try:
                    player.stopTransmit(self.getAudioMedia(-1))
                except Exception as e:
                    logger.error(f"Error stopping player: {e}")
            self.players = []

            if self.controller:
                logger.info(f"Destroy controller.")
                self.controller.destroy()
            else:
                logger.info(
                    f"When disconnecting the controller already destroyed.")

            # Unregister call from MyAccount
            # if self.controller and hasattr(self.controller.sip_handler, "calls"):
            #    if ci.id in self.controller.sip_handler.calls:
            #        del self.controller.sip_handler.calls[ci.id]
            #        info.logger(f"[INFO] Removed call ID {ci.id} from active calls.")

            # Allow garbage collection to delete this instance
            logger.info(f"Destroy Call instance.")
            time.sleep(0.5)
            del self

    def onCallMediaState(self, prm):
        logger.info(f"onCallMediaState: ----")
        ci = self.getInfo()
        # Loop through each media stream in the call.
        for i, mi in enumerate(ci.media):
            logger.info(
                f"[INFO][Call.onCallMediaState] media.type={mi.type} media.status={mi.status}")
            # Check if this media stream is audio.
            if hasattr(mi, 'type') and mi.type == pj.PJMEDIA_TYPE_AUDIO:
                # Check if its status indicates active media.
                if mi.status == pj.PJSUA_CALL_MEDIA_ACTIVE:
                    try:
                        self.event_connected.set()

                        # AudioMedia represents doorbell
                        self.audio_med = self.getAudioMedia(i)

                        # AudDevManager represents PC
                        self.aud_mgr = globals.pj_ep.audDevManager()

                        # it represents PC capture device like microphone (Piper TTS)
                        # self.mic_piper = self.aud_mgr.getCaptureDevMedia()
                        # intstead of capture from microphone play from file
                        # self.player = pj.AudioMediaPlayer()
                        # like: self.player.createPlayer("/tmp/test_mic.wav")

                        # it creates issue, not closes audio port
                        if globals.stt_app:
                            globals.stt_app.set_callback(self.playbackVoskText)
                        #    globals.stt_app.start(self.playbackVoskText)

                        # it represents PC playback device like speaker (vosk STT)
                        # like: player_media = self.aud_mgr.getPlaybackDevMedia()
                        self.speaker_vosk = self.aud_mgr.getPlaybackDevMedia()

                        # self.mic_piper.startTransmit(self.audio_med)
                        # self.player.startTransmit(self.audio_med)
                        # like: self.player.startTransmit(player_media)
                        self.audio_med.startTransmit(self.speaker_vosk)

                        # Connect to Vosk - ✅ Now detect & move the sink-input to vosk_stt
                        if globals.pulse_audio:
                            result = globals.pulse_audio.redirect_play_sink_input(
                                globals.pulse_audio.vosk.sink_id)
                            if not result:
                                logger.error(
                                    "❌ Could not find PJSUA2 stream for vosk in PulseAudio!")
                                return

                        if globals.tts_app:
                            globals.tts_app.start(self.audio_med)
                            # it works, moved to controller
                            # globals.tts_app.speak("You are welcome, please get in the house.")

                        # it works
                        # test_thd = threading.Timer(1, self.delayed_play)
                        # test_thd.start()

                        self.audio_active = True
                        # set timeout for connection
                        hang_thd = threading.Timer(120, self.hangupCall)
                        # logger.info(f"Start delayed hangup (5sec) in thd={hang_thd.name}")
                        hang_thd.start()

                    except Exception as e:
                        logger.error(
                            f"onCallMediaState: Error setting up TTS playback: {e}")

    def playbackVoskText(self, text):
        if self.controller:
            self.controller.receive_command(text)
        else:
            logger.error(f"Not defined controller.")

    def capturePiperText(self, text):
        if globals.tts_app:
            globals.tts_app.speak(text)
        else:
            logger.info(f"Not defined globals.tts_app.")

    def hangupCall(self):
        # logger.info(f" [sip:MyCall] hangupCall: started. - curThd={threading.current_thread().name}")
        if self.hangup_scheduled:
            logger.info(f"hangupCall alrady scheduled.")
            return

        self.hangup_scheduled = True
        # logger.info(f"MyCall: 🔴 start hangupCall")

        try:
            # Check if pj_ep is set
            if globals.pj_ep is None:
                logger.info(
                    f"[WARNING] Global endpoint is not set. Cannot register thread. - curThd={threading.current_thread().name}")
                return

            # if not globals.pj_ep.libIsThreadRegistered():
            globals.pj_ep.libRegisterThread("hangupCall")

            # Check if call is already terminated
            ci = self.getInfo()
            # logger.info(f"hangupCall current ci.state={ci.state}")
            if ci.state == pj.PJSIP_INV_STATE_DISCONNECTED:
                logger.info(
                    f"[WARNING] Attempted to hang up a call that's already disconnected.")
                return

            # PJSIP_ESESSIONTERMINATED

            # Remove reference before hangup to avoid double calls
            # if self.controller and hasattr(self.controller.sip_handler, "calls"):
            #    if ci.id in self.controller.sip_handler.calls:
            #        del self.controller.sip_handler.calls[ci.id]
            #        logger.info(f"[INFO] Removed call ID {ci.id} before hangup.")

            # logger.info(f"hangupCall: Hanging up the call...")

            op = pj.CallOpParam()
            op.statusCode = 200  # Using a valid response code for hangup.
            self.hangup(op)
            # logger.info(f"hangupCall: Call hangup successful.")

        except pj.Error as pj_err:
            logger.error(f"PJSUA2 Error during hangup: {pj_err}")
        except Exception as e:
            logger.error(f"Error: during hangup: {e}")


class MyAccount(pj.Account):
    def __init__(self, sip_event_connected):
        super().__init__()
        self.calls = {}
        self.event_connected = sip_event_connected

    def onIncomingCall(self, prm):
        # logger.info(f" [sip:MyAccount] onIncomingCall: rdataInfo={prm.rdata.info}  callId={prm.callId}")

        call = MyCall(self.event_connected, self, prm.callId)

        # Initialize Controller for this call
        controller = Controller(call)

        # pass Controller handler to Call instance
        call.setController(controller)
        self.calls[prm.callId] = call  # Keep reference.

        # Answer the call with 200 OK.
        call_prm = pj.CallOpParam()
        call_prm.statusCode = 200
        call.answer(call_prm)
        # logger.info(f"Answered incoming call with ID {prm.callId}. Active calls: {len(self.calls)}")
