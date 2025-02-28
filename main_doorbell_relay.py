#!/usr/bin/env python3

from config import *
import requests

"""
    Commands from console:
        for: Interkom/Przekaznik/Uruchom przekaznik przez HTTP:
            user: relay
            pass: akuvox_221

        $ curl -v "http://192.168.178.133:1088/fcgi/do?action=OpenDoor&UserName=relay&Password=akuvox_221&DoorNum=1"
        $ curl -k -v "https://192.168.178.133/fcgi/do?action=OpenDoor&UserName=relay&Password=akuvox_221&DoorNum=1"

"""

def open_door(ip, port, scheme, username, password, door_num="1"):
    """
    Open the specified door/relay using the Akuvox fcgi/do endpoint.
    
    :param ip: IP address of the door intercom (e.g., "192.168.178.133")
    :param port: Port for HTTP or HTTPS (e.g., 1088 for HTTP, 443 for HTTPS)
    :param scheme: "http" or "https"
    :param username: Credentials for the device (e.g., "relay")
    :param password: Credentials for the device (e.g., "akuvox_221")
    :param door_num: "1" or "2" for Relay A or B (or "SA"/"SB" in high security mode)
    :return: True if request succeeded (HTTP 200), otherwise False
    """
    # Construct the full endpoint. Example:
    #   http://192.168.178.133:1088/fcgi/do?action=OpenDoor&UserName=relay&Password=akuvox_221&DoorNum=1
    url = f"{scheme}://{ip}:{port}/fcgi/do"

    # Query parameters per the Akuvox documentation:
    #   action=OpenDoor
    #   UserName=<username>
    #   Password=<password>
    #   DoorNum=<"1","2","SA","SB">
    params = {
        "action": "OpenDoor",
        "UserName": username,
        "Password": password,
        "DoorNum": door_num,
    }

    try:
        # For self-signed certs over HTTPS, set verify=False.
        # We'll set verify=True for HTTP -> no SSL anyway, so it's ignored.
        verify_ssl = (scheme == "https")
        response = requests.get(
            url, params=params, timeout=5, verify=verify_ssl
        )

        if response.status_code == 200:
            print("Door command sent successfully!")
            print("Response:", response.text)
            return True
        else:
            print(f"HTTP {response.status_code} Error:", response.text)
            return False
    except requests.RequestException as e:
        print("Error during request:", e)
        return False

if __name__ == "__main__":
    # Example usage:
    # 1) Plain HTTP (port 1088)
    open_door(
        ip=VOX_DOMAIN,
        port=1088,
        scheme="http",
        username=VOX_RELAY_USER,
        password=VOX_RELAY_PASS,
        door_num="1"  # "1" = Relay A
    )

    # 2) HTTPS (port 443)
    # open_door(
    #     ip="192.168.178.133",
    #     port=443,
    #     scheme="https",
    #     username="relay",
    #     password="akuvox_221",
    #     door_num="1"
    # )







