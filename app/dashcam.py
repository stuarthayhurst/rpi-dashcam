#!/usr/bin/python3
import datetime
import os
import subprocess
import uuid

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

print("Starting dashcam...")

#Ensure the storage config exists
storageConfigPath = "storage-config.json"
if not config.ensureConfig(storageConfigPath, config.defaultStorageConfig):
  exit(1)

#Read the storage config, using defaults for missing values
storageConfig = config.readConfig(storageConfigPath, config.defaultStorageConfig)
if storageConfig is None:
  exit(1)

#Prepare the recording location
recordingPath = ""
diskPath = ""
if storageConfig.useDedicatedPart:
  #Check that the specified partition exists
  diskPath = f"/dev/disk/by-uuid/{storageConfig.storagePartUUID}"
  if not os.path.exists(diskPath):
    print(f"Couldn't find '{diskPath}'")
    exit(1)

  #Find a mount point for the partition
  while True:
    sessionId = uuid.uuid1()
    recordingPath = f"/tmp/rpi-dashcam-data-{sessionId}"
    try:
      os.mkdir(recordingPath)
      break
    except FileExistsError:
      continue

  #Mount the partition
  print(f"Remounting '{diskPath}' at '{recordingPath}'...")
  subprocess.run(["umount", "-q", diskPath])
  mountProcess = subprocess.run(["mount", diskPath, recordingPath])
  if mountProcess.returncode != 0:
    print(f"Failed to mount '{diskPath}' to '{recordingPath}'")
    exit(1)
else:
  #Set the recording path from the config
  recordingPath = config.resolvePath(storageConfig.fixedRecordingPath)

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
splitter = None
while not shutdown.is_set():
  fileName = pickFileName(recordingPath, getTimeString(), "mp4")

  if not recording:
    splitter = SplittableOutput(output = PyavOutput(fileName))
    picam2.start_recording(encoder, splitter)
    recording = True
  else:
    splitter.split_output(PyavOutput(fileName))

  print(f"Writing to '{fileName}' for {recordingConfig.duration} seconds")
  shutdown.wait(recordingConfig.duration)

print("Stopping dashcam...")

picam2.stop_recording()
print("Finished recording")

#Clean up after dedicated partition, if used
if storageConfig.useDedicatedPart:
  #Unmount the partition
  print(f"Unmounting '{diskPath}'...")
  unmountProcess = subprocess.run(["umount", "-q", diskPath])
  if unmountProcess.returncode != 0:
    print(f"Failed to unmount '{diskPath}'")
    exit(1)

  #Delete the mount point
  os.rmdir(recordingPath)
