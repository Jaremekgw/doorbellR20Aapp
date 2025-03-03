"""
documentation: https://face-recognition.readthedocs.io/en/latest/?badge=latest
"""
import os
import sys
import threading
import cv2
import face_recognition_models
import face_recognition
import signal
import numpy as np
import time
import requests  # used for HTTP command
from config import *
from controller import Controller
import proximity_server  # Import FastAPI module
from queue import Queue

frame_queue = Queue()

# Optionally, set QT_QPA_PLATFORM to use xcb (for X11) or offscreen to bypass Wayland issues.
# os.environ["QT_QPA_PLATFORM"] = "xcb"
# os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Suppress FFmpeg logging
os.environ["OPENCV_FFMPEG_DEBUG"] = "0"

# Create a threading event for shutdown
shutdown_event = threading.Event()
face_recognition_thread = None  # Track the active face recognition thread
face_recognition_running = False  # Track if face recognition is running

def signal_handler(sig, frame):
    print("Signal received, shutting down gracefully...")
    shutdown_event.set()

signal.signal(signal.SIGINT, signal_handler)

###############################################
# Global state for face detection filtering
detection_lock = threading.Lock()
last_face_name = None
detection_count = 0
first_detection_time = None
last_event_time = None
pause_until = 0
###############################################

def on_face_detected(recognized_name):
    """
    This function is called each time a face is detected.
    It applies a simple filter so that an event is only accepted
    if the same recognized name is received consecutively 5 times
    within 1400 milliseconds. If no event occurs for 500ms, the counter resets.
    Once an event is accepted, the counter is cleared and the function pauses for 5 seconds.
    After that, a new thread is spawned to handle the accepted event (e.g. capturing a picture
    and sending an HTTP command if the recognized face is known).
    """
    global last_face_name, detection_count, first_detection_time, last_event_time, pause_until

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

        # Check if we have 5 consecutive events within 1.4 seconds.
        if detection_count >= 5 and (current_time - first_detection_time) <= 1.4:
            print(f"Accepted event for {recognized_name}")
            # Clear the counter and set a pause of 5 seconds.
            detection_count = 0
            first_detection_time = None
            last_event_time = None
            pause_until = current_time + 5  # 5-second pause

            # Start a new thread to handle the accepted event.
            threading.Thread(target=handle_accepted_event, args=(recognized_name,), daemon=True).start()

def handle_accepted_event(recognized_name):
    doorbell = Controller(None)
    """
    This function is started in a new thread when a face detection event is accepted.
    It is responsible for taking a picture (you may integrate the actual capture logic)
    and, if the recognized face is not "Unknown", sending an HTTP command to open the door.
    """
    # Simulate taking a picture (replace with actual capture if needed)
    print("Taking picture...")

    # For example, you might save the current frame to a file:
    # cv2.imwrite("snapshot.jpg", frame)

    # If the recognized name is known, send an HTTP command.
    if recognized_name != "Unknown":
        doorbell.doorbell_relay(1)
        """
        try:
            # Replace the URL below with your actual door-opening command.
            url = f"http://door-controller/open?name={recognized_name}"
            response = requests.get(url)
            print(f"HTTP command sent to open door for {recognized_name}, response: {response.status_code}")
        except Exception as ex:
            print(f"Error sending HTTP command: {ex}")
        """
    else:
        print("Face is unknown; door will not be opened.")

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

def handle_face_detection(frame_queue):
    """
    Runs face recognition while sending frames to the main thread for display.
    """
    global face_recognition_running
    print("🔵 Face recognition started!")

    rtsp_url = R20A_RTSP_URL
    if rtsp_url is None:
        print("Error: RTSP URL not set.")
        face_recognition_running = False
        return

    cap_thread = VideoCaptureThread(rtsp_url).start()

    while not shutdown_event.is_set() and proximity_server.is_proximity_active():
        frame = cap_thread.read()
        if frame is None:
            continue

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
            on_face_detected(name)

            #print(f"Detected face: {name}")
            #if name != "Unknown":
            #    print(f"✅ Recognized {name}, triggering event!")
            #    doorbell = Controller(None)
            #    doorbell.doorbell_relay(1)

        # Send frame and face names to the GUI queue (Main Thread)
        frame_queue.put((frame, small_face_locations, face_names))

    print("🔴 Face recognition stopped (proximity lost).")
    cap_thread.stop()
    face_recognition_running = False

def display_gui(frame_queue):
    """
    Runs in the main thread and displays frames.
    """
    while not shutdown_event.is_set():
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

        if cv2.waitKey(1) & 0xFF == ord('q'):
            shutdown_event.set()
            break

    cv2.destroyAllWindows()

def start_face_recognition():
    """
    Wrapper function to restart face recognition properly.
    """
    global face_recognition_thread

    if face_recognition_thread and face_recognition_thread.is_alive():
        print("⚠️ Stopping old face recognition thread before restarting...")
        shutdown_event.set()
        face_recognition_thread.join()
        shutdown_event.clear()

    face_recognition_thread = threading.Thread(target=handle_face_detection, args=(frame_queue,), daemon=True)
    face_recognition_thread.start()

def main():
    print("🚀 Starting FastAPI server for proximity sensor...")
    server_thread = threading.Thread(target=proximity_server.start_fastapi_server, args=(start_face_recognition,), daemon=True)
    server_thread.start()

    print("🎥 Face recognition system is waiting for proximity events...")
    
    # Start GUI in the main thread
    display_gui(frame_queue)

if __name__ == "__main__":
    main()
