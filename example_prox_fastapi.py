from fastapi import FastAPI
import time
import threading

app = FastAPI()

# State tracking
last_event_time = 0  # Time of the last received heartbeat
proximity_active = False  # True = ON, False = OFF
CHECK_INTERVAL = 1  # How often to check for timeout (seconds)
TIMEOUT = 3.5  # If no heartbeat after this time, assume OFF


def monitor_proximity():
    """Background thread to detect when proximity goes OFF."""
    global proximity_active, last_event_time
    while True:
        time.sleep(CHECK_INTERVAL)
        if proximity_active and (time.time() - last_event_time) > TIMEOUT:
            print("Proximity OFF: No heartbeat received, assuming object is gone.")
            proximity_active = False


# Start the background monitoring thread
threading.Thread(target=monitor_proximity, daemon=True).start()


@app.get("/proximity")  # Accepts GET requests
@app.post("/proximity")  # Accepts POST requests (for future flexibility)
async def proximity_event():
    global last_event_time, proximity_active

    last_event_time = time.time()  # Update heartbeat time

    if not proximity_active:
        print("Proximity ON: Detected object!")
        proximity_active = True  # Mark as active

    return {"status": "Heartbeat received"}


if __name__ == "__main__":
    import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=5000)
    uvicorn.run(app, host="0.0.0.0", port=5000, log_level="warning")

