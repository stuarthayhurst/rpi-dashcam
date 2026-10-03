#!/usr/bin/python3
import datetime
import os

from threading import Event
import signal

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import PyavOutput, SplittableOutput

import config

def pickFileName(path, name, extension):
  index = 0
  newFilePath = os.path.join(path, f"{name}.{extension}")
  while os.path.exists(newFilePath):
    index += 1
    newFilePath = os.path.join(path, f"{name}-{index}.{extension}")

  return newFilePath

def getTimeString():
  return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

shutdown = Event()
def shutdownHandler(signalNumber, frame):
  print("Received shutdown request, stopping...")
  shutdown.set()


#Ensure the storage config exists
if not config.ensureConfig("storage-config.json", config.defaultStorageConfig):
  exit(1)

#Read the config, using defaults for missing values
storageConfig = config.readConfig("storage-config.json", config.defaultStorageConfig)
if storageConfig is None:
  exit(1)

bitRate = 1000000 * 8
width = 1920
height = 1080
duration = 5

picam2 = Picamera2()
config = picam2.create_video_configuration({'size': (width, height), 'format': 'YUV420'})
picam2.configure(config)

encoder = H264Encoder(bitrate=bitRate)

signal.signal(signal.SIGTERM, shutdownHandler)
signal.signal(signal.SIGINT, shutdownHandler)

recording = False
splitter = None
while not shutdown.is_set():
  fileName = pickFileName("./", getTimeString(), "mp4")

  if not recording:
    splitter = SplittableOutput(output=PyavOutput(fileName))
    picam2.start_recording(encoder, splitter)
    recording = True
  else:
    splitter.split_output(PyavOutput(fileName))

  print(f"Writing to {fileName} for {duration} seconds")
  shutdown.wait(duration)

picam2.stop_recording()
print("Done recording")
