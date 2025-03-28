"""
documentation: https://face-recognition.readthedocs.io/en/latest/?badge=latest
"""
import os
import multiprocessing
import threading
import cv2
import face_recognition
import signal
import numpy as np
import time

from helper import *
from config import *
from controller import Controller
import proximity_server  # Import FastAPI module
from queue import Queue
from collections import deque

# True - proximity starts thread start_face_recognition() for every event   Idle CPU = < 1%
# False - proximity set activity inside thread start_face_recognition()     Idle CPU = 13-14%
CONFIG_START_PROXIMITY_THD = False
# Allow display screen and show frames
CONFIG_ALLOW_DISPLAY_GUI = False
# Pause time after face was recognized to start next detection
CONFIG_PAUSE_TIME = 10

# Optionally, set QT_QPA_PLATFORM to use xcb (for X11) or offscreen to bypass Wayland issues.
os.environ["QT_QPA_PLATFORM"] = "xcb"
# os.environ["QT_QPA_PLATFORM"] = "offscreen" # qt.qpa.plugin: Could not find the Qt platform plugin "offscreen"

# Suppress FFmpeg logging
os.environ["OPENCV_FFMPEG_DEBUG"] = "0"

# Send frames from handle_face_detection() to display_gui()
frame_queue = Queue()
# Create a threading event for shutdown
shutdown_event = threading.Event()
# Multiprocessing Event from main(), delay for next recognition until sip disconnected
sip_event_connected = None
# Additional flag for sip connection state
sip_connection_active = False

# Track the active face recognition thread
face_recognition_thread = None
# Track if face recognition is running
face_recognition_running = False

def signal_handler(sig, frame):
    print("Signal received, shutting down gracefully...")
    shutdown_event.set()

signal.signal(signal.SIGINT, signal_handler)

# first_detection = True
###############################################
# Global state for face detection filtering
detection_lock = threading.Lock()
last_face_name = None
detection_count = 0
first_detection_time = None
last_event_time = None
pause_until = 0
###############################################

# Buffer for saving previous frames
frame_buffer = deque(maxlen=30)  # Store last 30 frames

def on_face_detected(frame, recognized_name):
    """
    This function is called each time a face is detected.
    It applies a simple filter so that an event is only accepted
    if the same recognized name is received consecutively 5 times
    within 1200 milliseconds. If no event occurs for 500ms, the counter resets.
    Once an event is accepted, the counter is cleared and the function pauses for 'CONFIG_PAUSE_TIME' seconds.
    After that, a new thread is spawned to handle the accepted event (e.g. capturing a picture
    and sending an HTTP command if the recognized face is known).
    """
    global last_face_name, detection_count, first_detection_time, last_event_time, pause_until
    global frame_buffer

    current_time = time.time()
    with detection_lock:
        # If we're in a forced pause period, do nothing.
        if current_time < pause_until:
            return

        # If more than 0.5 sec passed since last event, reset counter.
        if last_event_time is None or (current_time - last_event_time) > 0.5:
            detection_count = 0
            first_detection_time = current_time
            last_face_name = recognized_name

        # If same name as previous event, increment; otherwise, reset.
        if recognized_name == last_face_name:
            detection_count += 1
        else:
            detection_count = 1
            first_detection_time = current_time
            last_face_name = recognized_name

        last_event_time = current_time

        # Store frame in buffer
        frame_buffer.append(frame.copy())

        # Check if we have 5 consecutive events within 1.2 seconds.
        if detection_count >= 5 and (current_time - first_detection_time) <= 1.2:
            print(f"Accepted event for {recognized_name}")
            # Clear the counter and set a pause of 5 seconds.
            detection_count = 0
            first_detection_time = None
            last_event_time = None
            pause_until = current_time + CONFIG_PAUSE_TIME  # x-seconds pause
            # Start a new thread to handle the accepted event.
            threading.Thread(target=handle_accepted_event, args=(recognized_name,), daemon=True).start()

def handle_accepted_event(recognized_name):
    doorbell = Controller(None)
    global face_recognition_running
    global sip_connection_active
    global frame_buffer
    # global first_detection
    """
    This function is started in a new thread when a face detection event is accepted.
    It is responsible for taking a picture (you may integrate the actual capture logic)
    and, if the recognized face is not "Unknown", sending an HTTP command to open the door.
    """
    # Simulate taking a picture (replace with actual capture if needed)
    # print("Taking picture...")

    #if first_detection:
    #    first_detection = False
    #    current_time = get_current_time()
    #    print(f"[{current_time}] Taking picture...")
    #else:
    #    print("Taking picture...")
    print("Taking picture...")

    # For example, you might save the current frame to a file:
    # cv2.imwrite("snapshot.jpg", frame)

    # If the recognized name is known, send an HTTP command.
    if recognized_name != "Unknown":
        doorbell.doorbell_relay(1)
    else:
        print("Face is unknown; door will not be opened.")

    file_name = f""
    print("Face detected! Saving frames...")
    face_detected = True
    save_video(list(frame_buffer), recognized_name)
    frame_buffer.clear()  # Clear buffer after saving

    # after the face was recognized stop working
    face_recognition_running = False
    sip_connection_active = False
    print(f"[143] 🔴🔵 Face recognition, change running:{face_recognition_running}")

##################################################################
# The remainder of the code (video capture, face detection, etc.) remains as before.
##################################################################

# Load known face encodings and names from the "known_faces" directory.
known_face_encodings = []
known_face_names = []

def load_known_faces(known_faces_dir="known_faces"):
    if not os.path.isdir(known_faces_dir):
        print(f"Directory '{known_faces_dir}' not found. No known faces loaded.")
        return

    for filename in os.listdir(known_faces_dir):
        filepath = os.path.join(known_faces_dir, filename)
        # Only process image files (you can adjust the extensions as needed)
        if os.path.splitext(filename)[1].lower() not in [".jpg", ".jpeg", ".png"]:
            continue
        image = face_recognition.load_image_file(filepath)
        encodings = face_recognition.face_encodings(image)
        if len(encodings) > 0:
            known_face_encodings.append(encodings[0])
            # Use filename without extension as the person's name
            known_face_names.append(os.path.splitext(filename)[0])
            print(f"Loaded known face for {os.path.splitext(filename)[0]}")
        else:
            print(f"No face found in {filename}")

load_known_faces()  # Load known faces at startup

class VideoCaptureThread:
    def __init__(self, src):
        self.cap = cv2.VideoCapture(src)
        # Read the first frame
        self.grabbed, self.frame = self.cap.read()
        self.running = True
        self.lock = threading.Lock()
        self.thread = None

    def start(self):
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()
        return self

    def update(self):
        while self.running and not shutdown_event.is_set():
            ret, frame = self.cap.read()
            if not ret:
                continue  # In a live stream, wait for the next frame
            with self.lock:
                self.grabbed = ret
                self.frame = frame

    def read(self):
        with self.lock:
            return self.frame.copy() if self.frame is not None else None

    def stop(self):
        self.running = False
        if self.thread is not None:
            self.thread.join()
        self.cap.release()

# def handle_face_detection(frame_queue):
def handle_face_detection(set_active):
    """
    Runs face recognition while sending frames to the main thread for display.
    """
    #global first_detection
    global face_recognition_running
    global sip_connection_active
    # Track if face recognition is running
    proximity_active = set_active
    face_recognition_running = set_active
    if sip_event_connected:
        sip_connection_active = sip_event_connected.is_set()
    else:
        sip_connection_active = False
    print(f"[218] 🔵 Started  handle_face_detection() :{face_recognition_running}")

    # first_run = True
    #first_detection = True
    current_time = get_current_time()

    print(f"[{current_time}] 🔵 Face recognition started!")

    rtsp_url = R20A_RTSP_URL
    if rtsp_url is None:
        print("Error: RTSP URL not set.")
        return

    cap_thread = VideoCaptureThread(rtsp_url).start()

    """
    [20:49:34.902] 🟢 Proximity ON: Detected object! Starting face recognition...
    [20:49:34.903] 🔵 Face recognition started!
    [20:49:37.877] First VideoCaptureThread!
    [20:49:37.880] First frame!
    [20:49:38.054] First face.

    [21:10:43.873] 🟢 Proximity ON: Detected object! Starting face recognition...
    [21:10:43.874] 🔵 Face recognition started!
    [21:10:46.852] First VideoCaptureThread!    - after 3 sec
    [21:10:46.854] First frame!
    [21:10:47.012] First face.                  - after 158 ms
    Accepted event for JarekG2
    [21:10:47.644] Taking picture...
    """
    # current_time = get_current_time()
    # print(f"[{current_time}] First VideoCaptureThread!")

    while not shutdown_event.is_set() and (not CONFIG_START_PROXIMITY_THD or face_recognition_running):
        if sip_event_connected:
            if sip_connection_active == sip_event_connected.is_set():
                sip_connection_active = sip_event_connected.is_set()
                print(f"[218] 🔵🔵🔵 Sip connection changed, active:{sip_connection_active}")

        if proximity_active != proximity_server.is_proximity_active():
            proximity_active = proximity_server.is_proximity_active()
            #if sip_event_connected:
            #    if sip_event_connected.is_set():
            # face recognition action is changing its state
            face_recognition_running = proximity_active
            print(f"[261] 🔴🔵 Face recognition, change running:{face_recognition_running}")

        if face_recognition_running:
            frame = cap_thread.read()
            if frame is None:
                continue

            #if first_run:
            #    current_time = get_current_time()
            #    print(f"[{current_time}] First frame!")

            # Resize for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            # Convert from BGR to RGB and ensure contiguous array
            small_rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            small_rgb_frame = np.ascontiguousarray(small_rgb_frame)

            # Detect faces.
            """ another way, one by one
            small_face_locations = face_recognition.face_locations(
                small_rgb_frame, number_of_times_to_upsample=1, model='hog'
            )

            # Compute face encodings for each detected face
            small_face_encodings = []
            face_names = []        #
            for face_location in small_face_locations:
                try:
                    # Use the basic usage as in the docs: pass image and a list containing the location
                    encoding = face_recognition.face_encodings(small_rgb_frame, [face_location])[0]
                    small_face_encodings.append(encoding)
                except Exception as e:
                    print(f"Error computing encoding for face at {face_location}: {e}")
                    small_face_encodings.append(None)
            """

            small_face_locations = face_recognition.face_locations(small_rgb_frame, model='hog')
            small_face_encodings = [face_recognition.face_encodings(small_rgb_frame, [loc])[0] for loc in small_face_locations]

            #if first_run:
            #    first_run = False
            #    current_time = get_current_time()
            #    print(f"[{current_time}] First face.")

            face_names = []
            # Compare encodings with known faces
            for encoding in small_face_encodings:
                if encoding is None:
                    name = "Unknown"
                else:
                    try:
                        matches = face_recognition.compare_faces(known_face_encodings, encoding, tolerance=0.6)
                        name = "Unknown"
                        if True in matches:
                            first_match_index = matches.index(True)
                            name = known_face_names[first_match_index]
                    except Exception as e:
                        print("Error during face comparison:", e)
                        name = "Error"
                face_names.append(name)
                # Invoke the filtering callback for each detected face.
                on_face_detected(frame, name)

                #print(f"Detected face: {name}")
                #if name != "Unknown":
                #    print(f"✅ Recognized {name}, triggering event!")
                #    doorbell = Controller(None)
                #    doorbell.doorbell_relay(1)

            if CONFIG_ALLOW_DISPLAY_GUI:
                # Send frame and face names to the GUI queue (Main Thread)
                frame_queue.put((frame, small_face_locations, face_names))

        else:
            time.sleep(0.1)

    print("🔴 Face recognition stopped (proximity lost).")
    cap_thread.stop()

def display_gui():
    """
    Runs in the main thread and displays frames.
    """
    while not shutdown_event.is_set():
        if not CONFIG_ALLOW_DISPLAY_GUI:
            time.sleep(0.2)
            continue

        if not frame_queue.empty():
            frame, face_locations, face_names = frame_queue.get()

            # Draw rectangles and labels
            for (face_location, name) in zip(face_locations, face_names):
                top, right, bottom, left = face_location
                top, right, bottom, left = top * 4, right * 4, bottom * 4, left * 4
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
                cv2.rectangle(frame, (left, bottom - 20), (right, bottom), (0, 255, 0), cv2.FILLED)
                cv2.putText(frame, name, (left + 6, bottom - 6), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 0, 0), 1)

            cv2.imshow('Face Recognition', frame)
        else:
            time.sleep(0.05)

        if cv2.waitKey(10) & 0xFF == ord('q'):
            shutdown_event.set()
            break

    cv2.destroyAllWindows()

def start_face_recognition(active):
    """
    Wrapper function to restart face recognition properly.
    """
    global face_recognition_thread

    if face_recognition_thread and face_recognition_thread.is_alive():
        print("⚠️ Stopping old face recognition thread before restarting...")
        shutdown_event.set()
        face_recognition_thread.join()
        shutdown_event.clear()

    # face_recognition_thread = threading.Thread(target=handle_face_detection, args=(frame_queue,), daemon=True)
    face_recognition_thread = threading.Thread(target=handle_face_detection, args=(active, ), daemon=True)
    face_recognition_thread.start()


def save_video(frames, recognized_name="Unknown", fps=20):
    """ Saves the stored frames into a video file """
    if not frames:
        return
    
    date_string = get_current_date_time()
    output_path = SYS_FACES_PATH + date_string + "_" + recognized_name + ".avi"
    height, width, _ = frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    for frame in frames:
        out.write(frame)
    
    out.release()

def main(sip_event):
    global face_recognition_enable_event
    print("🚀 Starting FastAPI server for proximity sensor...")

    if CONFIG_START_PROXIMITY_THD:
        server_thread = threading.Thread(target=proximity_server.start_fastapi_server, args=(start_face_recognition,), daemon=True)
    else:
        server_thread = threading.Thread(target=proximity_server.start_fastapi_server, args=(None,), daemon=True)
        threading.Thread(target=start_face_recognition, args=(False, ), daemon=True).start()
    server_thread.start()

    face_recognition_enable_event = sip_event
    print("🎥 Face recognition system is waiting for proximity events...")
    #if face_event.is_set():
    #    print("🟢 Face Recognition ENABLED")
    #else:
    #    print("🔴 Face Recognition DISABLED")
    
    # Start GUI in the main thread
    # display_gui(frame_queue)
    display_gui()

    #while True:
    #    if face_event.is_set():
    #        print("🟢 Face Recognition ENABLED")
    #    else:
    #        print("🔴 Face Recognition DISABLED")
    #        time.sleep(1)  # Prevent CPU overuse

if __name__ == "__main__":
    sip_event_con = multiprocessing.Event()
    sip_event_con.clear()
    main(sip_event_con)
