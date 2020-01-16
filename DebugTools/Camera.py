import io
import picamera
import logging
import socketserver
from threading import Condition
from http import server
import numpy as np
from PIL import Image
import matplotlib as mpl
from matplotlib import cm
import itertools

cm_jet = cm.jet

motion_dtype = np.dtype([
    ('x', 'i1'),
    ('y', 'i1'),
    ('sad', 'u2'),
    ])

PAGE="""\
<html>
<head>
<title>Landscraper</title>
</head>
<body>
<center><h1>Landscraper - Debug</h1></center>
<center><img src="stream.mjpg" width="640" height="480"></center>
</body>
</html>
"""

class StreamingOutput(object):
    def __init__(self):
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()

    def write(self, buf):
        if buf.startswith(b'\xff\xd8'):
            # New frame, copy the existing buffer's content and notify all
            # clients it's available
            self.buffer.truncate()
            with self.condition:
                self.frame = self.buffer.getvalue()
                self.condition.notify_all()
            self.buffer.seek(0)
        return self.buffer.write(buf)

class MyMotionDetector(object):
    def __init__(self, camera):
        width, height = camera.resolution
        self.cols = (width + 15) // 16
        self.cols += 1  # there's always an extra column
        self.rows = (height + 15) // 16
        self.findex = 0
        self.skipFrames = 10
        self.frameCounter = 0
        self.frame = None
        self.buffer = io.BytesIO()
        self.condition = Condition()
        self.heatmap = np.full((self.rows, self.cols), 0.0, dtype=np.float)

    def write(self, s):
        # Load the motion data from the string to a numpy array
        data = np.frombuffer(s, dtype=motion_dtype)
        # Re-shape it and calculate the magnitude of each vector
        data = data.reshape((self.rows, self.cols))
        data = np.sqrt(
            np.square(data['x'].astype(np.float)) +
            np.square(data['y'].astype(np.float))
        ).clip(0, 255) / 255
        if self.frameCounter > self.skipFrames:
            for x, y in itertools.product(range(self.rows), range(self.cols)):
                if data[x, y] > 0.3:
                    self.heatmap[x, y] += 0.1
                    #print("Bumped value to %f" % self.heatmap[x, y])
                else:
                    self.heatmap[x, y] *= 0.99

            img = Image.fromarray(np.uint8(cm_jet(self.heatmap) * 255))
            self.findex += 1
            filename = 'frame%03d.png' % self.findex
            #print('Writing %s' % filename)
            img.save(filename)
        else:
            self.frameCounter += 1

        #self.frame = self.buffer.getvalue()
        #self.buffer.write()

        #print(np.amax(self.heatmap))


        return len(s)

        # If there're more than 10 vectors with a magnitude greater
        # than 60, then say we've detected motion
        #if (data > 60).sum() > 10:
        #    print('Motion detected!')
        # Pretend we wrote all the bytes of s
        #return len(s)

class StreamingHandler(server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(301)
            self.send_header('Location', '/index.html')
            self.end_headers()
        elif self.path == '/index.html':
            content = PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(content))
            self.end_headers()
            self.wfile.write(content)
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
            self.send_error(404)
            self.end_headers()

class StreamingServer(socketserver.ThreadingMixIn, server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

with picamera.PiCamera(resolution='1640x1232') as camera:
    #motion_output = MyMotionDetector(camera)
    #output = StreamingOutput()
    camera.start_recording(
        output='raw.h264',
        format='h264'#,
        #motion_output='motion.data'
    )
    camera.wait_recording(15)
    camera.stop_recording()
    #camera.start_recording(output, format='mjpeg')
   # try:
    #    address = ('', 8000)
    #    server = StreamingServer(address, StreamingHandler)
    #    server.serve_forever()
    #finally:
    #    camera.stop_recording()

