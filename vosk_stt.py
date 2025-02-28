import pyaudio
import threading
import sys
from vosk import Model, KaldiRecognizer
from config import VOSK_MODEL_PATH
import json

class VoskSTT:
    def __init__(self, model_path, pa_manager):
        # get access to Virtual Pulse Audio Devices
        self.pa_manager = pa_manager

        # Create model from the link to file 
        self.model = Model(model_path)
        # Initialize the recognizer with the given model and sample rate
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.recognizer.SetWords(True)

        self.p = pyaudio.PyAudio()
        self.running = False
        self.callback = None
        print(f"Vosk: ✅ initialized")

    def set_callback(self, callback):
        self.callback = callback

    def start(self, callback=None):
        """
            Open an input stream using the given device index
        python has acces only to hardware, list and select 'pipewire'
        """
        self.callback = callback
        hw_id = None

        for i in range(self.p.get_device_count()):
            dev = self.p.get_device_info_by_index(i)
            if "pipewire" in dev['name']:
                hw_id = i
                break

        if hw_id is None:
            print("❌ No HW audio device (pipewire) found. Exiting...")
            return

        print(f"Vosk: 🎙️ start model on device id: {hw_id}")
        self.stream = self.p.open(format=pyaudio.paInt16,
                                  channels=1,
                                  rate=16000,
                                  input=True,
                                  frames_per_buffer=8000,
                                  input_device_index=hw_id) # connect to default

        # check if interface is available and redirect to sink.monitor(source)
        result = self.pa_manager.redirect_cap_source_output(self.pa_manager.vosk.sink_id)
        if not result:
            print("❌ Could not find VOSK(source-output) stream in PulseAudio!")
            return

        self.running = True
        # Start the audio processing thread
        self.thread = threading.Thread(target=self.run)
        print(f"Vosk: ✅ initialize thread: {threading.current_thread().name}")
        self.thread.start()
        print("Vosk: 🎙️ Listening...!")

    def run(self):
        while self.running:
            try:
                data = self.stream.read(8000, exception_on_overflow=False)
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    if "text" in result and result["text"].strip() != "":
                        # print(f"Recognized Text: {result['text']}")
                        if self.callback:
                            self.callback(result["text"])
                #else:
                #    partial = self.recognizer.PartialResult()

            except Exception as e:
                print(f"Error reading stream: {e}")
                continue
 
    def stop(self):
        """Stops the STT processing."""
        print(f"VoskSST: stop  running={self.running}")
        self.callback = None
        if self.running:
            self.running = False
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.p.terminate()
            self.thread.join()
            print(f"VoskSST: 🔴 STT stopped.")
        else:
            print(f"VoskSST: 🔴 STT already stopped.")
