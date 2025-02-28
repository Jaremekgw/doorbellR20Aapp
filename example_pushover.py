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

if __name__ == "__main__":
    # Replace these with your own Pushover credentials
    MESSAGE = "Hello from Linux!"

    resp = send_message(PUSH_USER_KEY, PUSH_API_TOKEN, MESSAGE)
    print(resp.text)

