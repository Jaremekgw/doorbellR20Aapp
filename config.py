# config.py

import os

# pushover credential
PUSH_USER_KEY=os.getenv("PUSH_USER_KEY", "123456789")
PUSH_API_TOKEN=os.getenv("PUSH_API_TOKEN", "123456789")

# server with SIP (raspberry Pi)
SIP_DOMAIN = os.getenv("SIP_DOMAIN", "192.168.10.3")
SIP_USER = os.getenv("SIP_USER", "sip_user")
SIP_PASS = os.getenv("SIP_PASS", "sip_pass")
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "5060"))

# doorbell R20A
R20A_RTSP_URL = os.getenv("R20A_RTSP_URL", "rtsp://192.168.10.230/live/ch00_0")
VOX_DOMAIN = os.getenv("VOX_DOMAIN", "192.168.10.230")
VOX_HTTP_PORT = os.getenv("VOX_HTTP_PORT", "1088")
VOX_RELAY_USER = os.getenv("VOX_RELAY_USER", "user_rel")
VOX_RELAY_PASS = os.getenv("VOX_RELAY_PASS", "abcd_rel")

# system folders
SYS_LOG_PATH = "log/"
SYS_FACES_PATH = "storage/"

LANGUAGE = "PL"
# LANGUAGE = "EN"

# ---- TTS PIPER
# Piper project: https://github.com/rhasspy/piper
# Training Guide: https://github.com/rhasspy/piper/blob/master/TRAINING.md
PIPER_EXECUTABLE = os.getenv("PIPER_EXECUTABLE", "/data/programs/piper/piper")
# Voices to download: https://github.com/rhasspy/piper/blob/master/VOICES.md
# PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", "/data/models/piper/en_GB-jenny_dioco-medium.onnx")
PIPER_MODEL_PATH = os.getenv("PIPER_MODEL_PATH", "/data/models/piper/pl_PL-gosia-medium.onnx")

# ---- STT Vosk
# Vosk project: https://alphacephei.com/vosk/
# Models to download: https://alphacephei.com/vosk/models
# Lightweight model for Polish
VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", "/data/models/vosk/vosk-model-small-pl-0.22")
# Big US English model with dynamic graph
# VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", "/data/models/vosk/vosk-model-en-us-0.22-lgraph")
#  	Lightweight wideband model for Android and RPi
# VOSK_MODEL_PATH = os.getenv("VOSK_MODEL_PATH", "/data/models/vosk/vosk-model-small-en-us-0.15")


