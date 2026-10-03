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
storageConfigPath = "storage-config.json"
if not config.ensureConfig(storageConfigPath, config.defaultStorageConfig):
  exit(1)

#Read the storage config, using defaults for missing values
storageConfig = config.readConfig(storageConfigPath, config.defaultStorageConfig)
if storageConfig is None:
  exit(1)

#Ensure the recording config exists
recordingConfigPath = os.path.join(storageConfig.recordingPath, "recording-config.json")
if not config.ensureConfig(recordingConfigPath, config.defaultRecordingConfig):
  exit(1)

#Read the recording config, using defaults for missing values
recordingConfig = config.readConfig(recordingConfigPath, config.defaultRecordingConfig)
if recordingConfig is None:
  exit(1)

#Set the recording path from the config
recordingPath = config.resolvePath(storageConfig.recordingPath)

picam2 = Picamera2()
config = picam2.create_video_configuration({'size': (recordingConfig.width, recordingConfig.height), 'format': 'YUV420'})
picam2.configure(config)

encoder = H264Encoder(bitrate = recordingConfig.bitRate)

signal.signal(signal.SIGTERM, shutdownHandler)
signal.signal(signal.SIGINT, shutdownHandler)

recording = False
splitter = None
while not shutdown.is_set():
  fileName = pickFileName(recordingPath, getTimeString(), "mp4")

  if not recording:
    splitter = SplittableOutput(output = PyavOutput(fileName))
    picam2.start_recording(encoder, splitter)
    recording = True
  else:
    splitter.split_output(PyavOutput(fileName))

  print(f"Writing to {fileName} for {recordingConfig.duration} seconds")
  shutdown.wait(recordingConfig.duration)

picam2.stop_recording()
print("Done recording")
