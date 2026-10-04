import datetime
import os
import subprocess
import uuid

import config

def getTimeString():
  return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

def pickRecordingFile(path, extension):
  name = getTimeString()

  index = 0
  newFilePath = os.path.join(path, f"{name}.{extension}")
  while os.path.exists(newFilePath):
    index += 1
    newFilePath = os.path.join(path, f"{name}-{index}.{extension}")

  return newFilePath

def getPartByConfig(storageConfig):
  return f"/dev/disk/by-uuid/{storageConfig.storagePartUUID}"

#Read the config and choose a storage path
def chooseRecordingPath(storageConfig):
  #Use the fixed path and return early if possible
  if not storageConfig.useDedicatedPart:
    return config.resolvePath(storageConfig.fixedRecordingPath)

  #If configured to use a partition, create, prepare and return a mount point
  recordingPath = ""
  if storageConfig.useDedicatedPart:
    #Check that the specified partition exists
    diskPath = getPartByConfig(storageConfig)
    if not os.path.exists(diskPath):
      print(f"Couldn't find '{diskPath}'")
      return None

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
      return None

  return recordingPath

def closeRecordingPath(storageConfig, recordingPath):
  #Clean up after dedicated partition, if used
  if storageConfig.useDedicatedPart:
    #Unmount the partition
    diskPath = getPartByConfig(storageConfig)
    print(f"Unmounting '{diskPath}'...")
    unmountProcess = subprocess.run(["umount", "-q", diskPath])
    if unmountProcess.returncode != 0:
      print(f"Failed to unmount '{diskPath}'")
      return False

    #Delete the mount point
    os.rmdir(recordingPath)

  return True

def getStorageFreeBytes(storagePath):
  st = os.statvfs(storagePath)
  freeBlocks = st.f_bavail
  blockSize = st.f_frsize

  return freeBlocks * blockSize

def getOldestRecording(storagePath):
  #Sorting by filename will place the oldest first, assuming all files are managed by this program
  fileList = os.listdir(storagePath)
  fileList.sort()

  #Find the first recording in the list
  oldestFile = None
  for file in fileList:
    if file.endswith(".mp4"):
      oldestFile = file
      break

  if oldestFile is not None:
    return os.path.join(storagePath, oldestFile)
  else:
    return None

def rotateStorage(storageConfig, storagePath):
  firstPass = True

  #Figure out how much storage is being used
  storageFreeBytes = getStorageFreeBytes(storagePath)
  storageThresholdBytes = storageConfig.rotationThresholdBytes

  #Clean up storage while too much is being used
  while storageFreeBytes <= storageThresholdBytes:
    if firstPass:
      storageFreeGiB = round(storageFreeBytes / (1024 * 1024 * 1024), 2)
      storageThresholdGiB = round(storageThresholdBytes / (1024 * 1024 * 1024), 2)
      print(f"Storage free space insufficient ({storageFreeGiB} GiB <= {storageThresholdGiB} GiB), looking for recordings to delete")
      firstPass = False

    #Find the oldest recording to delete
    targetFile = getOldestRecording(storagePath)
    if targetFile is None:
      print("No recordings found to free")
      return False

    #Delete the selected file
    print(f"Deleting {targetFile}")
    os.remove(targetFile)

    storageFreeBytes = getStorageFreeBytes(storagePath)

  return True
