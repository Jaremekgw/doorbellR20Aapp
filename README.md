# "Smart Doorbell Assistant"

An AI-powered smart doorbell system that automatically answers calls, recognizes faces, and manages visitor interactions. It integrates RTSP protocol for video streaming, SIP for handling, and HTTP for automation, providing a seamless and intelligent home security experience.

## run app

1. set virtual environment for python

```sh
pyenv activate venv3.10
# install requred libraries if first time
pip install -r requirements.txt
```

2. run face recognition and smart doorbell

```sh
# start face recognition
python main_face.py
# start smart doorbell
python main.py
```

