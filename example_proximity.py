import time
import datetime
from flask import Flask, request

app = Flask(__name__)

@app.route('/proximity', methods=['GET', 'POST'])
def proximity_event():
    # t = time.localtime()
    # ms = time.time_ns() 
    # current_time = time.strftime("%H:%M:%S", t)

    time_now = datetime.datetime.now()
    # current_time = time_now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    current_time = time_now.strftime('%H:%M:%S.%f')[:-3]
    print(f"Proximity sensor triggered! time:{current_time}")
    # Here you can trigger face recognition
    return "OK", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

