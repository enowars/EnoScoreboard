#!/usr/bin/env python3

import threading
import random
import string
import json
from flask import Flask, render_template, send_from_directory
from flask_socketio import SocketIO
from pathlib import Path


app = Flask(__name__)
app.config['SECRET_KEY'] = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(16))
socketio = SocketIO(app)

SCOREBOARD_JSON = "/data/scoreboard.json"

@app.route('/js/<path:filename>')
def serve_js(filename):
    return send_from_directory("./js/",filename)

@app.route('/css/<path:filename>')
def serve_css(filename):
    return send_from_directory("./css/",filename)

@app.route('/webfonts/<path:filename>')
def serve_webfonts(filename):
    return send_from_directory("./webfonts/",filename)

@app.route('/')
def serve_index():
    return send_from_directory("./","index.html")

@socketio.on('reloadScoreboard')
def send_scoreboard(data):
    try:
        return Path(SCOREBOARD_JSON).read_text()
    except Exception as e:
        print("Exception while reading scoreboard.json: ", e)

def scoreboard_updater_thread():
    def modification_watcher():
        import time
        import os
        mod_time = 0
        while True:
            try:
                stat = os.stat(SCOREBOARD_JSON)
                if mod_time != stat.st_mtime:
                    print("Change detected!")
                    mod_time = stat.st_mtime
                    socketio.emit('updateScoreboard', Path(SCOREBOARD_JSON).read_text(), json=True)
                    print("Updated the scoreboard!")
            except Exception as e:
                print("Exception while checking file: ", e)
            time.sleep(0.25)
    t = threading.Thread(target=modification_watcher)
    t.start()


@app.before_first_request
def start_thread():
    scoreboard_updater_thread()

if __name__ == '__main__':
    scoreboard_updater_thread()
    socketio.run(app)