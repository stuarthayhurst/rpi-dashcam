#!/usr/bin/python3
import os
import time

from threading import Event
import signal

from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from picamera2.outputs import PyavOutput, SplittableOutput

import config
import storageManager

shutdown = Event()
def shutdownHandler(signalNumber, frame):
  print("Received shutdown request, stopping...")
  shutdown.set()

print("Starting dashcam...")

#Ensure the storage config exists
storageConfigPath = "storage-config.json"
if not config.ensureConfig(storageConfigPath, config.defaultStorageConfig):
  exit(1)

#Read the storage config, using defaults for missing values
storageConfig = config.readConfig(storageConfigPath, config.defaultStorageConfig)
if storageConfig is None:
  exit(1)

#Prepare a storage location for recordings
recordingPath = storageManager.chooseRecordingPath(storageConfig)
if recordingPath is None:
  exit(1)
print(f"Using '{recordingPath}' for recording storage")

#Ensure the recording config exists
recordingConfigPath = os.path.join(recordingPath, "recording-config.json")
if not config.ensureConfig(recordingConfigPath, config.defaultRecordingConfig):
  exit(1)

#Read the recording config, using defaults for missing values
recordingConfig = config.readConfig(recordingConfigPath, config.defaultRecordingConfig)
if recordingConfig is None:
  exit(1)

print("Preparing camera and encoder...")
picam2 = Picamera2()
config = picam2.create_video_configuration({'size': (recordingConfig.width, recordingConfig.height), 'format': 'YUV420'})
picam2.configure(config)

encoder = H264Encoder(bitrate = recordingConfig.bitRate)

#Gracefully stop recording on shutdown
signal.signal(signal.SIGTERM, shutdownHandler)
signal.signal(signal.SIGINT, shutdownHandler)

#Continuously record into files with a fixed max length
recording = False
failed = False
splitter = None
while not shutdown.is_set():
  fileName = storageManager.pickRecordingFile(recordingPath, "mp4")

  #Start or split the recording
  if not recording:
    splitter = SplittableOutput(output = PyavOutput(fileName))
    picam2.start_recording(encoder, splitter)
    recording = True
  else:
    splitter.split_output(PyavOutput(fileName))

  recordingStartTime = time.time()
  print(f"Writing to '{fileName}' for {recordingConfig.duration} seconds")

  #Handle storage rotation
  if not storageManager.rotateStorage(storageConfig, recordingPath):
    print("Failed to rotate storage, exiting")
    failed = True
    break

  #Wait for the rest of the recording time
  remainingTime = recordingConfig.duration - (time.time() - recordingStartTime)
  if remainingTime > 0:
    shutdown.wait(remainingTime)

print("Stopping dashcam...")

picam2.stop_recording()
print("Finished recording")

#Clean up after the storage location
if not storageManager.closeRecordingPath(storageConfig, recordingPath):
  exit(1)

if failed:
  exit(1)
