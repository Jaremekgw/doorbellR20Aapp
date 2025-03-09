# helper.py

import datetime

def get_current_time():
    time_now = datetime.datetime.now()
    return time_now.strftime('%H:%M:%S.%f')[:-3]

