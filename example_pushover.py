import requests
from config import *

"""
    This is a minimal Python example using the Pushover API
    (requires signing up for a user key and registering an app 
    to get an API token).

    Another service for push notifications is:
      - https://ntfy.sh (5$/mth/3phone)
      - https://gotify.net/	(free)
"""

def send_message(user_key, app_token, message):
    url = "https://api.pushover.net/1/messages.json"
    data = {
        "token": app_token,
        "user": user_key,
        "message": message
    }
    response = requests.post(url, data=data)
    return response


def send_message_with_image(user_key, app_token, message, image_path):
    """
        Sending push with picture, remember to meet picture size requirements
    """
    url = "https://api.pushover.net/1/messages.json"
    data = {
        "token": app_token,
        "user": user_key,
        "message": message
    }
    with open(image_path, "rb") as img_file:
        files = {"attachment": img_file}
        response = requests.post(url, data=data, files=files)
    return response


if __name__ == "__main__":
    # Replace these with your own Pushover credentials
    MESSAGE = "Hello from Linux!"

    # send only message
    resp = send_message(PUSH_USER_KEY, PUSH_API_TOKEN, MESSAGE)
    print(resp.text)

    # send message with picture
    IMAGE_PATH = "path_to_your_image.jpg"
    resp = send_message_with_image(PUSH_USER_KEY, PUSH_API_TOKEN, MESSAGE, IMAGE_PATH)
    print(resp.text)
