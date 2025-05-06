import subprocess
import time
import re

"""
    Manages PulseAudio Virtual Devices for Vosk STT and Piper TTS.
    - for now only Vosk is used

    see different solution: app_pa_virt/virtual_audio.py
    import pulsectl
    self.sink_id = self.pulse.module_load('module-null-sink', 'sink_name=VirtualSink sink_properties=device.description=VirtualSink')
    self.source_id = self.pulse.module_load('module-remap-source', 'master=VirtualSink.monitor source_name=VirtualMic')
    # This loopback connects the virtual sink to the virtual mic
    self.loopback_id = self.pulse.module_load('module-loopback', 'source=VirtualSink.monitor sink=VirtualMic')
    print(f"Created Virtual Sink (ID: {self.sink_id}), Virtual Mic (ID: {self.source_id}), and Loopback (ID: {self.loopback_id})")


    Sprawdzic czy zadziala przed podlaczeniem do audio 'pipewire' ustawic default:
        $ pactl set-default-sink PiperSink

    for debug: switch on: '❌ Could not find' '⏳ Waiting for PJSUA2'
        
"""

VIRT_DEV_VOSK_SINK_NAME = "VoskSink"
VIRT_DEV_PIPER_SINK_NAME = "PiperSink"


class DevStruct:
    def __init__(self, name):
        self.name = name
        self.module = None      # module = pactl load-module module-null-sink = 536870916
        # = pactl list sinks | grep -B7 'Owner Module: 536870916' = Sink #64040
        self.sink_id = None
        self.sk_input = None
        self.src_out = None


class SwitchModule:
    def __init__(self):
        self.sin_cnt = 0
        self.sin_mod_id = [0, 0]
        self.sin_sink_id = [0, 0]
        self.src_cnt = 0
        self.src_mod_id = [0, 0]
        self.src_sink_id = [0, 0]


class PulseAudioVirtualDevices:
    def __init__(self):
        self.swich = SwitchModule()
        # for Vosk STT
        self.vosk = DevStruct(VIRT_DEV_VOSK_SINK_NAME)
        # self.piper = DevStruct(VIRT_DEV_PIPER_SINK_NAME)            # for Piper TTS

        # create and store reference indexes
        # self.vosk_module_id, self.vosk_sink_id = self.create_vosk_dev()     # for Vosk STT
        self.vosk.module, self.vosk.sink_id = self.create_virtual_dev(
            self.vosk.name)     # for Vosk STT
        # self.piper.module, self.piper.sink_id = self.create_virtual_dev(self.piper.name)  # for Piper TTS

    def search_module_null_sink(self, sink_name):
        """
            Search module 'module-null-sink' with following name  
            to check if exists
            used only by create_vosk_dev()
        """
        module_id = None
        module_name = None
        cmd = f"pactl list modules | grep -B2 -A7 '{sink_name}'"
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if "Module #" in line:
                module_id = int(re.search(r'\d+', line).group())
            if "Name:" in line:
                module_name = line.split("\t")[1]  # Get the value for name

            if module_id and module_name:
                if "module-null-sink" in module_name:
                    # correct module with virtual sink device
                    break
                else:
                    module_id = None
                    module_name = None
        return module_id

    def create_virtual_dev(self, sink_name):
        """
            Create module-null-sink
        """
        sink_id = None

        # before create check if it not already exists
        module_id = self.search_module_null_sink(sink_name)
        if module_id is None:
            result = subprocess.run(["pactl", "load-module", "module-null-sink",
                                     f"sink_name={sink_name}",
                                     f"sink_properties=device.description={sink_name}"],
                                    capture_output=True, text=True)
            module_id = result.stdout.strip()

        """
        Now we have module id. find sink id using this command:
            $ pactl list sinks | grep -B7 'Owner Module: 536870916'
        """
        cmd = f"pactl list sinks | grep -B7 'Owner Module: {module_id}'"
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True)
        # Split the output into lines
        lines = result.stdout.strip().split("\n")
        # Print only the first line
        if lines:
            sink_id = int(re.search(r'\d+', lines[0]).group())

        print(
            f">>>> PulseAudio: ✅ virtual device: Name:{sink_name}  Module:{module_id} Sink:{sink_id}")
        return module_id, sink_id

    def remove_module(self, id):
        """Removes the Virtual module with id."""
        subprocess.run(["pactl", "unload-module", str(id)])
        print(f"🧹 Removed Virtual module (ID: {id})")

    def cleanup(self):
        """Removes all virtual devices on exit."""
        if self.vosk.module:
            self.remove_module(self.vosk.module)
        # if self.piper.module:
        #     self.remove_module(self.piper.module)

    def get_vosk_monitor(self, sink_name):
        """Finds the monitor source of the VoskSink in PulseAudio."""
        result = subprocess.run(
            ["pactl", "list", "sources", "short"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if sink_name in line and "monitor" in line:
                return line.split("\t")[0]  # Get the monitor source name
        # print(f"❌ Could not find VirtualSink monitor for {sink_name}")
        return None

    def get_piper_sink(self):
        """Finds the sink of the PiperSource in PulseAudio."""
        result = subprocess.run(
            ["pactl", "list", "sinks", "short"], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if self.piper_source_name in line:
                return line.split("\t")[0]  # Get the sink name
        # print(f"❌ Could not find VirtualSink for {self.piper_source_name}")
        return None

    def redirect_play_sink_input(self, play_sink_id):
        """
            Redirect PJSUA2 stream to Vosk (VoskSink)

            piper_tts.py:91:        success = self.pa_manager.redirect_play_sink_input(self.pa_manager.piper.sink_id)
            (vosk)sip_handler.py:178:     result = globals.pulse_audio.redirect_play_sink_input(globals.pulse_audio.vosk.sink_id)
        """
        if play_sink_id != self.vosk.sink_id and play_sink_id != self.piper.sink_id:
            print(
                f"❌ Wrong sink id #{play_sink_id} for redirect playback! (Vosk#{self.vosk.sink_id} Piper#{self.piper.sink_id})")
            return False

        # brak rozroznienia czy to dla Vosk czy Piper
        # trzeba zapisac do zmiennych zeby nie przekierowac niewlasciwego
        sin_module_id, sin_sink_id = self.find_playback_sink_input()

        if sin_module_id is None or sin_sink_id is None:
            # print("❌ Could not find PJSUA2(sink-input) stream in PulseAudio!")
            return False

        if sin_sink_id == play_sink_id:
            # no need to move-sink-input
            # print(f">>>> RedirectSin: ✅ sink-input already set,  ID:{sin_module_id}  sink:{sin_sink_id}")
            return True

        # print(f">>>> RedirectSin: ✅ move-sink-input,  ID:{sin_module_id}  from:{sin_sink_id}  sink:{play_sink_id}")
        cmd = f"pactl move-sink-input {sin_module_id} {play_sink_id}"
        subprocess.run(cmd, shell=True)
        return True

    def redirect_cap_source_output(self, capture_sink_id):
        """
            Redirect Vosk source-output to Vosk (VoskSink.monitor)

            (piper)sip_handler.py:186:     result = globals.pulse_audio.redirect_cap_source_output(globals.pulse_audio.piper_sink_i
            vosk_stt.py:50:         result = self.pa_manager.redirect_cap_source_output(self.pa_manager.vosk_sink_id)
        """
        if capture_sink_id != self.vosk.sink_id and capture_sink_id != self.piper.sink_id:
            print("❌ Wrong sink id for redirect capture!")
            return False

        # brak rozroznienia czy to dla Vosk czy Piper
        # trzeba zapisac do zmiennych zeby nie przekierowac niewlasciwego
        src_module_id, src_sink_id = self.find_capture_source_output()

        if src_module_id is None or src_sink_id is None:
            print("❌ Could not find VOSK(source-output) stream in PulseAudio!")
            return False

        if src_sink_id == capture_sink_id:
            # no need to move-sink-input
            # print(f">>>> RedirectSrc: ✅ source-output already set,  ID:{src_module_id}  sink:{src_sink_id}")
            return True

        # print(f">>>> RedirectSrc: ✅ move-source-output,  ID:{src_module_id}  from:{src_sink_id}  sink:{capture_sink_id}")
        cmd = f"pactl move-source-output {src_module_id} {capture_sink_id}"
        subprocess.run(cmd, shell=True)
        return True

    def find_playback_sink_input(self):
        # was: find_pjsua2_sink_input
        """
            Used only by: redirect_play_sink_input()

            Finds the sink-input ID for PJSUA2's playback in PulseAudio.

        Sink Input #104                                                 <-- sink_input_id
                Driver: PipeWire
                Owner Module: n/a
                Client: 103
                Sink: 62                                                <-- sink_id
                Sample Specification: s16le 1ch 16000Hz
                Channel Map: mono
        ...
                Resample method: PipeWire
                Properties:
                        remote.name = "pipewire-0"                      <-- device_name
                        application.name = "PipeWire ALSA [python3.10]"
                        node.name = "alsa_playback.python3.10"
                        device.description = "ALSA Playback [python3.10]"
                        media.name = "ALSA Playback"
                        media.type = "Audio"
                        media.category = "Playback"                     <--
                        node.latency = "320/16000"
                        node.rate = "1/16000"
                        stream.is-live = "true"
                        node.want-driver = "true"
                        node.autoconnect = "true"
                        media.class = "Stream/Output/Audio"        
        ...
        """
        device_name = "pipewire"    # expected 'remote.name = "pipewire-0"'
        sink_input_id = None
        sink_id = None

        #    piper_tts.py:91:        success = self.pa_manager.redirect_play_sink_input(self.pa_manager.piper.sink_id)
        #    (vosk)sip_handler.py:178:     result = globals.pulse_audio.redirect_play_sink_input(globals.pulse_audio.vosk.sink_id)

        for _ in range(3):      # Retry loop to wait for the sink-input to appear
            print(f"------   check interfaces sink-inputs   ------ wait  0s100ms")
            time.sleep(0.1)     # Wait for playback to start
            result = subprocess.run(
                ["pactl", "list", "sink-inputs"], capture_output=True, text=True)
            lines = result.stdout.splitlines()

            print(f"  [find_playback_sink_input] -->>")
            potential_id = None
            potential_sink = None
            line1 = None
            line2 = None

            for i, line in enumerate(lines):
                if "Sink Input #" in line:
                    line1 = line
                    # potential_id = line.split("#")[1].strip()
                    potential_id = int(re.search(r'\d+', line).group())

                elif "Sink:" in line:
                    line2 = line
                    potential_sink = int(re.search(r'\d+', line).group())

                elif "remote.name" in line and device_name in line:
                    print(f"    {line1}")
                    print(f"    {line2}")
                    print(f"    {line}")

                    cnt = self.swich.sin_cnt
                    if cnt > 0:
                        if cnt == 1 and self.swich.sin_mod_id[0] != potential_id:
                            self.swich.sin_mod_id[cnt] = potential_id
                            self.swich.sin_sink_id[cnt] = potential_sink
                            print(
                                f">>>> SwitchSin: ✅ added:{cnt}  mod:{potential_id}  sink:{potential_sink}")
                            self.swich.sin_cnt = cnt + 1
                            sink_input_id = potential_id  # ✅ Found the correct sink-input
                            sink_id = potential_sink
                    else:
                        self.swich.sin_mod_id[cnt] = potential_id
                        self.swich.sin_sink_id[cnt] = potential_sink
                        print(
                            f">>>> SwitchSin: ✅ added:{cnt}  mod:{potential_id}  sink:{potential_sink}")
                        self.swich.sin_cnt = cnt + 1
                        sink_input_id = potential_id  # ✅ Found the correct sink-input
                        sink_id = potential_sink

                    potential_id = None
                    potential_sink = None
                    line1 = None
                    line2 = None
                    # break  # Stop after finding the first match

            if sink_input_id and sink_id:
                break
            # print("⏳ Waiting for PJSUA2 to create a sink-input...")

        if sink_input_id is None or sink_id is None:
            # print("❌ Could not find PJSUA2 stream in PulseAudio!")
            return None, None

        print(
            f" ✅ find_playback_sink_input: return ID:{sink_input_id}  sink_id:{sink_id}")
        return sink_input_id, sink_id

    def find_capture_source_output(self):
        """
            Used only by: redirect_cap_source_output()

        """
        device_name = "pipewire"    # expected 'remote.name = "pipewire-0"'
        source_output_id = None
        source_id = None

        for _ in range(3):      # Retry loop to wait for the sink-input to appear

            print(f"------   check interfaces source-outputs   ------ wait  0s100ms")
            time.sleep(0.1)     # Wait for playback to start
            cmd = f"pactl list source-outputs"
            # result = subprocess.run(["pactl", "list", "sink-inputs"], capture_output=True, text=True)
            # wrong: subprocess.run(cmd, capture_output=True, text=True)
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True)
            lines = result.stdout.splitlines()

            potential_id = None
            potential_source = None
            line1 = None
            line2 = None

            # print(f"  [find_capture_source_output] -->>")

            for i, line in enumerate(lines):
                if "Source Output" in line:
                    line1 = line
                    # potential_id = line.split("#")[1].strip()
                    potential_id = int(re.search(r'\d+', line).group())

                elif "Source:" in line:
                    line2 = line
                    potential_source = int(re.search(r'\d+', line).group())

                elif "remote.name" in line and device_name in line:
                    # print(f"    {line1}")
                    # print(f"    {line2}")
                    # print(f"    {line}")

                    cnt = self.swich.src_cnt
                    if cnt > 0:
                        if cnt == 1 and self.swich.src_mod_id[0] != potential_id:
                            self.swich.src_mod_id[cnt] = potential_id
                            self.swich.src_sink_id[cnt] = potential_source
                            # print(f">>>> SwitchSrc: ✅ added:{cnt}  mod:{potential_id}  source:{potential_source}")
                            self.swich.src_cnt = cnt + 1
                            source_output_id = potential_id  # ✅ Found the correct sink-input
                            source_id = potential_source
                    else:
                        self.swich.src_mod_id[cnt] = potential_id
                        self.swich.src_sink_id[cnt] = potential_source
                        # print(f">>>> SwitchSrc: ✅ added:{cnt}  mod:{potential_id}  source:{potential_source}")
                        self.swich.src_cnt = cnt + 1
                        source_output_id = potential_id  # ✅ Found the correct sink-input
                        source_id = potential_source

                    potential_id = None
                    potential_source = None
                    line1 = None
                    line2 = None
                    # break  # Stop after finding the first match

            if source_output_id and source_id:
                break
            # print("⏳ Waiting for Capture device to create a source-output...")

        if source_output_id is None or source_id is None:
            print("❌ Could not find Capture stream in PulseAudio!")
            return
        # print(f" ✅ find_capture_source_output: return ID:{source_output_id}  source_id:{source_id}")
        return source_output_id, source_id


if __name__ == "__main__":
    pa_manager = PulseAudioVirtualDevices()
    try:
        pa_manager.create_vosk_dev()
        pa_manager.create_piper_dev()
    except KeyboardInterrupt:
        pa_manager.cleanup()

        """
    def create_vosk_dev(self):  # don't use it
        Steps:
            - create another virtual sink:
            pactl load-module module-null-sink sink_name=PiperSink

            - If Piper outputs to a default audio device, 
              set PiperSink as the default sink before running Piper:
            pactl set-default-sink PiperSink

            - If you need to route specific application audio to the virtual sink, use pactl or pavucontrol:
            - Find the Piper TTS playback stream:
            pactl list short sink-inputs
            - Redirect it to PiperSink:
            pactl move-sink-input <sink-input-ID> PiperSink

            - Connecting PiperSink to Doorbell
            - To route PiperSink to the doorbell output, you need a loopback:
            pactl load-module module-loopback source=PiperSink.monitor sink=<DOORBELL_SINK>

        Creates a PulseAudio VirtualSink for Vosk STT.
            example:
            $ $ pactl load-module module-null-sink sink_name=VirtualSink sink_properties=device.description=VoskSink
            536870916
            $ pactl list modules | grep -A6 '536870916'
            Module #536870916
                Name: module-null-sink
                Argument: sink_name=VoskSink sink_properties=device.description=VoskSink
                Usage counter: n/a
                Properties:
                    module.author = "Wim Taymans <wim.taymans@gmail.com>"
                    module.description = "A NULL sink"
                    ...
        Check this device:
            $ pactl list sinks short
            64040	VirtualSink	PipeWire	float32le 2ch 48000Hz	SUSPENDED

            $ pactl list sources short
            64040	VirtualSink.monitor	PipeWire	float32le 2ch 48000Hz	SUSPENDED

            $ pactl list sinks | grep -B7 'Owner Module: 536870916'
            Sink #64040
                State: SUSPENDED
                Name: VirtualSink
                Description: VoskSink
                Driver: PipeWire
                Sample Specification: float32le 2ch 48000Hz
                Channel Map: front-left,front-right
                Owner Module: 536870916

        """

        """
    def find_capture_source_output(self):
            Finds the sink-input ID for PJSUA2's playback in PulseAudio.

        Source Output #77806                                            <-- source_output_id
                Driver: PipeWire
                Owner Module: n/a
                Client: 77805
                Source: 77105                                           <-- source_id
                Sample Specification: s16le 1ch 16000Hz
                Channel Map: mono
        ...
                Resample method: PipeWire
                Properties:
                        remote.name = "pipewire-0"                      <-- device_name
                        application.name = "PipeWire ALSA [python3.10]"
                        node.name = "alsa_capture.python3.10"
                        device.description = "ALSA Capture [python3.10]"
                        media.name = "ALSA Capture"
                        media.type = "Audio"
                        media.category = "Capture"                      <--
                        node.latency = "8000/16000"
                        node.rate = "1/16000"
                        stream.is-live = "true"
                        node.want-driver = "true"
                        node.autoconnect = "true"
                        media.class = "Stream/Input/Audio"
        ...

        
    $ pactl list source-outputs | grep -A 20 'Source Output #'
    Source Output #86934
    	Driver: PipeWire
    	Owner Module: n/a
    	Client: 86933
    	Source: 84518
    	Sample Specification: s16le 1ch 16000Hz
    	Channel Map: mono
    	Format: pcm, format.sample_format = "\"s16le\""  format.rate = "16000"  format.channels = "1"  format.channel_map = "\"mono\""
    	Corked: no
    	Mute: no
    	Volume: mono: 65536 / 100% / 0.00 dB
	            balance 0.00
    	Buffer Latency: 0 usec
    	Source Latency: 0 usec
    	Resample method: PipeWire
    	Properties:
    		remote.name = "pipewire-0"
    		application.name = "PipeWire ALSA [python3.10]"
    		node.name = "alsa_capture.python3.10"
    		device.description = "ALSA Capture [python3.10]"
    		media.name = "ALSA Capture"

        """
