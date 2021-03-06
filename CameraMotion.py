import numpy as np
import picamera
import picamera.array
import socket
import itertools
import struct
import asyncio
from threading import Condition
import scipy as sp
import scipy.ndimage
import cv2
from PIL import Image
from matplotlib import cm

#hostMACAddressBluetooth = 'DC:A6:32:2C:68:23'
#portBluetooth = 3
#s = socket.socket(socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM)
#s.bind((hostMACAddressBluetooth, portBluetooth))

hostIpAdressEther = '192.168.2.151'
portEther = 50001
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind((hostIpAdressEther, portEther))

backlog = 1
s.listen(backlog)

width = 1640
height = 1232
cols = (width + 15) // 16
cols += 1  # = 104
rows = (height + 15) // 16  # = 77

sigma = [5.0, 5.0]
frame = 0

# Due to the last two columns having faulty motion data at times we ignore those,
# we will fix this later by scaling the heatmap to our desired resolution
_heatmap = np.full((rows, cols-2), 0.5, dtype=np.float32)


class DetectMotion(picamera.array.PiMotionAnalysis):
    def __init__(self, c):
        super(DetectMotion, self).__init__(c)
        self.condition = Condition()
        self.heatmap = np.full((rows, cols), 0.5, dtype=np.float32)

    def analyze(self, a):
        data = np.sqrt(
            np.square(a['x'].astype(np.float)) +
            np.square(a['y'].astype(np.float))
            ).clip(0, 255).astype(np.uint8)
        for x, y in itertools.product(range(rows), range(cols)):
            if y >= (cols - 2):
                continue
            if data[x, y] > 30:
                self.heatmap[x, y] += np.float32(0.1)
            else:
                self.heatmap[x, y] *= np.float32(0.99)
        self.heatmap.clip(np.float32(0.0), np.float32(1.0))

        with self.condition:
            self.condition.notify_all()


print("Waiting for client")
client, address = s.accept()
print("Client connected")


async def periodic():
    global _heatmap, frame
    while True:
        await asyncio.sleep(3)
        heatmap_blurred = sp.ndimage.filters.gaussian_filter(_heatmap, sigma)
        heatmap_resized = cv2.resize(heatmap_blurred, dsize=(65, 65))
        buffer = struct.pack("4225f", *(heatmap_resized.flatten()))
        img = Image.fromarray(np.uint8(cm.jet(heatmap_resized) * 255))
        filename = 'frame%04d.png' % frame
        print('Writing %s' % filename)
        img.save(filename)
        frame += 1
        print("Sending %d bytes" % len(buffer))
        print(buffer)
        client.sendall(buffer)


async def analyze():
    global _heatmap
    with picamera.PiCamera() as camera:
        with DetectMotion(camera) as output:
            camera.resolution = (width, height)
            camera.start_recording('/dev/null', format='h264', motion_output=output) #, resize=(1040, 1040))
            while True:
                with output.condition:

                    await asyncio.sleep(1)
                    output.condition.wait()
                    #print("Updating heatmap with dimensions x: %d y: %d" % (len(output.heatmap), len(output.heatmap[0])))
                    _heatmap = np.copy(output.heatmap)


def stop():
    task.cancel()
    task2.cancel()


loop = asyncio.get_event_loop()
task = loop.create_task(periodic())
task2 = loop.create_task(analyze())

try:
    loop.run_until_complete(task)
    loop.run_until_complete(task2)
except asyncio.CancelledError:
    pass

                    # raw_command = client.recv(1)
                    # command, = struct.unpack('B', raw_command)
                    # print("Got command %d" % command)


                    # chunks = list(funcy.chunks(4, output.heatmap.tobytes()))
                    # for chunk in chunks:

                    # buffer = struct.pack("8008f", *(output.heatmap.flatten()))
                    # print("Sending %d bytes" % len(buffer))
                    # client.send(buffer)

                    # print(output.heatmap.shape)

                    # for x in range(0, rows):
                    #     for y in range(0, cols):
                    #         buffer = b''
                    #         xpart = struct.pack("I", x)
                    #         #print("xpart: %s" % xpart)
                    #         buffer += xpart
                    #         ypart = struct.pack("I", y)
                    #         #print("ypart: %s" % ypart)
                    #         buffer += ypart
                    #         heightpart = struct.pack("f", output.heatmap[x, y])
                    #         #print("heightpart: %s" % output.heatmap[x, y])
                    #         buffer += heightpart
                    #         #print(buffer)
                    #         print("Sending %d bytes" % len(buffer))
                    #         client.sendall(buffer)

                    # x = np.array([[0, 1], [2, 3]])
                    # client.send(x.tobytes())
