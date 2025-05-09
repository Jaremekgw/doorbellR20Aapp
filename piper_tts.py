# tts.py

import pyaudio
import os
import time
import wave
import tempfile
import threading
import subprocess
import globals

from config import PIPER_EXECUTABLE
import pjsua2 as pj
from logger_config import get_logger

# Must be set BEFORE importing pyaudio or opening the stream
os.environ["PULSE_PROP_application.name"] = "PiperTTS"
os.environ["PULSE_PROP_media.name"] = "Piper TTS Playback"

active = False
logger = get_logger(__name__)


class PiperTTS:
    def __init__(self, pa_manager, model_path="/path/to/model.onnx"):
        """
        Manages Piper TTS using PyAudio for playback.

        Args:
            pa_manager: Your PulseAudioVirtualDevices instance (for sink redirection, etc.).
            model_path (str): Path to the Piper TTS model (.onnx).
        """
        self.tts_text = "Hello! Someone is at your door."
        self.audio_active = False

        self.pa_manager = pa_manager
        self.model_path = model_path
        self.players = []  # List to hold multiple AudioMediaPlayer instances
        self.audio_med = None

        self.p = pyaudio.PyAudio()
        self.stream_out = None
        self.running = False

        logger.info("PiperTTS: ✅ initialized")

    def start(self, audio_media):
        if self.audio_med:
            logger.info("PiperTTS: Already started.")
            return
        logger.info("PiperTTS: started.")
        self.audio_med = audio_media

    def speak(self, text):
        """
        Open the PyAudio output stream once, so we can reuse it for multiple speak() calls.
        Also perform sink redirection after the stream is open.
        """
        if self.audio_med is None:
            logger.info("PiperTTS: Not started.")
            return

        self.audio_active = True
        # play_thd = threading.Timer(0.2, self.play_tts, args=(text,))
        play_thd = threading.Thread(target=self.play_tts, args=(text,))
        # logger.info(f"Start TTS play in thread={play_thd.name}")
        self.running = True
        play_thd.start()

        # logger.info("PiperTTS: 🔵 TTS stream started and ready to speak.")

    def stop(self):
        """
        Close the PyAudio output stream and release resources.
        """
        if self.running:
            self.running = False

            if self.stream_out is not None:
                self.stream_out.stop_stream()
                self.stream_out.close()
                self.stream_out = None

            self.p.terminate()
            logger.info("PiperTTS: 🔴 TTS stopped.")
        else:
            logger.info("PiperTTS: Already stopped.")

    def play_tts(self, tts_text):
        # Generate and play TTS message
        if not self.audio_active:
            logger.info(f"[WARNING] Try to play TTS without active audio.")
            return

        logger.info(f"PiperTTS:  🔊 play: '{tts_text}'")
        time_begin = time.time()
        wav_file = self.generate_tts_wav(tts_text)
        if not wav_file:
            logger.info(f"[ERROR] TTS generation failed; skipping playback.")
            return

        try:
            # Get the duration of the audio file
            with wave.open(wav_file, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / float(rate)  # Duration in seconds

            time_generate_wav = time.time() - time_begin

            # if not globals.pj_ep.libIsThreadRegistered():
            # logger.info(f"play_tts: Register thd=({threading.current_thread().name}) -----------------")
            globals.pj_ep.libRegisterThread("dynamic_tts")

            # Create AudioMediaPlayer and stream the WAV into the call
            player = pj.AudioMediaPlayer()
            player.createPlayer(wav_file, pj.PJMEDIA_FILE_NO_LOOP)
            player.startTransmit(self.audio_med)
            self.players.append(player)

            # logger.info(f"play_tts: Playing file={wav_file}, "
            #       f"gen_time={time_generate_wav:.2f}s, duration={duration:.2f}s")

        except wave.Error as we:
            logger.error(
                f"[Exception] Wave error while reading WAV file: {we}")
        except Exception as e:
            logger.error(
                f"[Exception] Unexpected error while playing TTS response: {e}")

    def generate_tts_wav(self, text):
        """
        Generate a WAV file from text using Piper TTS.

        Args:
            text (str): The text to convert to speech.

        Returns:
            str or None: Path to the generated WAV file, or None if generation failed.

            print instead of  logging.info  logging.error
        """
        # logger.info(f"Called method: generate_tts_wav(text={text}) curThd={threading.current_thread().name}")

        # Audio parameters
        sample_rate = 22050  # Hz         this setting is expected, don't change it
        # sample_rate = 16000  # Hz         nie moge tego ustawic, spowalnia mowe
        sample_width = 2     # bytes (16-bit)
        channels = 1         # Mono

        # Create a temporary WAV file
        tmp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_wav_path = tmp_wav.name
        tmp_wav.close()

        # PIPER_MODEL_PATH
        try:
            # Run Piper and capture its raw output
            cmd = [
                PIPER_EXECUTABLE,
                "--model", self.model_path,
                "--output-raw"
            ]

            # logger.info(f"Generating TTS audio for text: '{text}'")
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # Send the text to Piper's stdin and capture stdout and stderr
            raw_audio, stderr = proc.communicate(input=text.encode('utf-8'))

            if proc.returncode != 0:
                error_message = stderr.decode().strip()
                logger.error(f"Piper error: {error_message}")
                os.unlink(tmp_wav_path)
                return None

            # Write raw audio data to WAV file with proper headers
            with wave.open(tmp_wav_path, 'wb') as wav_file:
                wav_file.setnchannels(channels)
                wav_file.setsampwidth(sample_width)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(raw_audio)

            # logging.info(f"Generated TTS WAV file: {tmp_wav_path}")
            # logger.info(f"Finishing method: generate_tts_wav() curThd={threading.current_thread().name}  WAV file: {tmp_wav_path}")
            return tmp_wav_path

        except Exception as e:
            logger.error(f"Error generating TTS file: {e}")
            if os.path.exists(tmp_wav_path):
                os.unlink(tmp_wav_path)
            return None
