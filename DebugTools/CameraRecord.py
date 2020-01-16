import picamera

camera = picamera.PiCamera()
camera.resolution = (1640, 1232)
camera.framerate = 30
print("Recording ...")
camera.start_recording(
    output='raw.h264',
    format='h264',
    motion_output='motion.data',
    resize=(1040, 1040)
)
camera.wait_recording(40)
camera.stop_recording()
print("Done.")
