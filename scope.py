#!/usr/bin/python3

# This is the same as mjpeg_server.py, but uses the h/w MJPEG encoder.

import io
import logging
import socketserver
import urllib.parse
from http import server
from threading import Condition
from pprint import pprint

from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput

# hq camera max video capture is 2028x1520
# MJPEGEncoder max capture is 1920x1536
video_width = 1920
video_height = 1520

fps = 40
micro = int((1 / fps) * 1e6)

tuning = Picamera2.load_tuning_file("imx477_scientific.json")
picam2 = Picamera2(tuning=tuning)

common = {
    "AeEnable":     False,
    "AwbEnable":    False,
    "AnalogueGain": 1.0,
    "Sharpness":    0
}

surface_detail = {
    "ExposureTime": 10000,
    "Brightness":   -0.05,
    "Contrast":     1.81,
    "Saturation":   1.1,
    "ColourGains":  (0.69, 1.33)
} | common

prominence_detail = {
    "ExposureTime": 79000,
    "Brightness":   -0.44,
    "Contrast":     3.12,
    "Saturation":   0.82,
    "ColourGains":  (0.9, 1.83)
} | common

# video config
video_config = picam2.create_video_configuration(
    main={
        "size": (video_width, video_height)
    }
)

video_config["controls"]["FrameDurationLimits"] = (micro, micro)

video_config["controls"] = surface_detail

picam2.configure(video_config)


# still config
still_config = picam2.create_still_configuration(
    main={
        "size": picam2.sensor_resolution
    }
)


mjpegencoder = MJPEGEncoder()


class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()


class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        global red_gain
        global blue_gain
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            PAGE = f"""
<html>
<head>
<title>picamera2 MJPEG streaming demo</title>
</head>
<body>
<iframe name="dummyframe" id="dummyframe" style="display: none;"></iframe>
<a href="/capture" download="single.png"><button>Capture Image</button></a>
<a href="/capture_surface" download="surface.png"><button>Capture Surface</button></a>
<a href="/capture_prominence" download="prominence.png"><button>Capture Prominence</button></a>
<form target="dummyframe" id=config action="/configure" oninput="document.forms['config'].submit()">
  <label for="exposure">Exposure Time:</label>
  <input type="number" id="exposure" name="exposure" min="1000" max="200000" step="1000" value={picam2.camera_configuration()["controls"]['ExposureTime']} >
  <label for="brightness">Brightness:</label>
  <input type="range" id="brightness" name="brightness" min="-1.0" max="1.0" step="0.01" value={picam2.camera_configuration()["controls"]['Brightness']} >
  <label for="contrast">Contrast:</label>
  <input type="range" id="contrast" name="contrast" min="0.0" max="10.0" step="0.01" value={picam2.camera_configuration()["controls"]['Contrast']} >
  <label for="saturation">Saturation:</label>
  <input type="range" id="saturation" name="saturation" min="0.0" max="2.2" step="0.01" value={picam2.camera_configuration()["controls"]['Saturation']} >
  <label for="redgain">Red Gain:</label>
  <input type="range" id="redgain" name="redgain" min="0.0" max="32.0" step="0.01" value={picam2.camera_configuration()["controls"]["ColourGains"][0]} >
  <label for="bluegain">Blue Gain:</label>
  <input type="range" id="bluegain" name="bluegain" min="0.0" max="32.0" step="0.01" value={picam2.camera_configuration()["controls"]["ColourGains"][1]} >
  <input type="submit" value="Submit">
</form>
<a target="dummyframe" href="/reset"><button>Reset</button></a>
<h1>Picamera2 MJPEG Streaming Demo</h1>
<img src="stream.mjpg" width="{video_width}" height="{video_height}" />
</body>
</html>
""".encode("utf-8")
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(PAGE))
            self.end_headers()
            self.wfile.write(PAGE)
        elif self.path == '/favicon.ico':
            self.send_response(200)
            self.send_header('Content-Type', 'image/x-icon')
            self.send_header('Content-Length', 0)
            self.end_headers()

        elif self.path == '/reset':
            self.send_response(205)
            picam2.controls.set_controls(surface_detail)

        elif self.path.startswith('/configure'):
            self.send_response(204)
            try:
                parms = urllib.parse.parse_qs(self.path[11:])
                print(self.path[11:])
                print(parms)
                if len(parms) > 0:
                    if "exposure" in parms.keys():
                        picam2.controls.ExposureTime = int(parms["exposure"][0])
                    if "brightness" in parms.keys():
                        picam2.controls.Brightness = float(parms["brightness"][0])
                    if "contrast" in parms.keys():
                        picam2.controls.Contrast = float(parms["contrast"][0])
                    if "saturation" in parms.keys():
                        picam2.controls.Saturation = float(parms["saturation"][0])
                    if "redgain" in parms.keys():
                        red_gain = float(parms["redgain"][0])
                        blue_gain = picam2.camera_configuration()["controls"]["ColourGains"][1]
                        picam2.controls.ColourGains = (red_gain, blue_gain)
                    if "bluegain" in parms.keys():
                        red_gain = picam2.camera_configuration()["controls"]["ColourGains"][0]
                        blue_gain = float(parms["bluegain"][0])
                        picam2.controls.ColourGains = (red_gain, blue_gain)
            except Exception as e:
                logging.warning(
                    str(parms)
                )
                logging.warning(
                    str(e)
                )

        elif self.path.startswith('/capture'):
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Content-type', 'image/png')
            self.end_headers()
            if self.path == '/capture_surface':
                still_config['controls'] = surface_detail
            elif self.path == '/capture_prominence':
                still_config['controls'] = prominence_detail
            else:
                still_config['controls'] = picam2.camera_configuration()["controls"]
            try:
                data = io.BytesIO()
                picam2.stop_encoder()
                picam2.switch_mode(still_config)
                picam2.switch_mode_and_capture_file(still_config, data, format='png', wait=False)
            except Exception as e:
                logging.warning(
                    str(e)
                )
            finally:
                pprint(picam2.camera_configuration()["controls"])
                picam2.switch_mode(video_config)
                picam2.start_encoder(mjpegencoder)
                self.wfile.write(data.getvalue())

        elif self.path == '/stream.mjpg':
            self.send_response(200)
            self.send_header('Age', 0)
            self.send_header('Cache-Control', 'no-cache, private')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=FRAME')
            self.end_headers()
            try:
                while True:
                    with output.condition:
                        output.condition.wait()
                        frame = output.frame
                    self.wfile.write(b'--FRAME\r\n')
                    self.send_header('Content-Type', 'image/jpeg')
                    self.send_header('Content-Length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except Exception as e:
                logging.warning(
                    'Removed streaming client %s: %s',
                    self.client_address, str(e))
        else:
            logging.warning(self.path)
            self.send_error(404)
            self.end_headers()


class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

output = StreamingOutput()
picam2.start_recording(mjpegencoder, FileOutput(output))

try:
    address = ('', 8000)
    server = StreamingServer(address, StreamingHandler)
    server.serve_forever()
finally:
    picam2.stop_recording()
