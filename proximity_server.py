# proximity_server.py

import time
import datetime
import threading
import uvicorn
from fastapi import FastAPI

app = FastAPI()

# Global state tracking
last_event_time = 0  
proximity_active = False  
CHECK_INTERVAL = 1  
TIMEOUT = 3.5  
proximity_callback = None  # Function to trigger face recognition

def monitor_proximity():
    """Background thread to detect when proximity goes OFF."""
    global proximity_active, last_event_time
    while True:
        time.sleep(CHECK_INTERVAL)
        if proximity_active and (time.time() - last_event_time) > TIMEOUT:
            time_now = datetime.datetime.now()
            current_time = time_now.strftime('%H:%M:%S.%f')[:-3]
            print(f"[{current_time}] 🔴 Proximity OFF: No heartbeat received, stopping face recognition.")
            proximity_active = False

# Start the background monitoring thread
threading.Thread(target=monitor_proximity, daemon=True).start()

@app.get("/proximity")  
@app.post("/proximity")  
async def proximity_event():
    global last_event_time, proximity_active

    last_event_time = time.time()  

    if not proximity_active:
        time_now = datetime.datetime.now()
        current_time = time_now.strftime('%H:%M:%S.%f')[:-3]
        print(f"[{current_time}] 🟢 Proximity ON: Detected object! Starting face recognition...")
        proximity_active = True  

        # Trigger the face recognition process
        if proximity_callback:
            threading.Thread(target=proximity_callback, args=(proximity_active, ), daemon=True).start()

    return {"status": "Heartbeat received"}

def is_proximity_active():
    """Returns True if proximity sensor is still detecting motion"""
    return proximity_active  # Used in face recognition loop

def start_fastapi_server(callback):
    """Start FastAPI in a separate thread."""
    global proximity_callback
    proximity_callback = callback  # Set the callback function for face recognition
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="warning")
