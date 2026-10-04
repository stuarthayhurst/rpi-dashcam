import os, json

class Config:
  def toDict(self):
    return self.__dict__

  def fromDict(self, dict):
    for key in dict:
      setattr(self, key, dict[key])

    return self

class StorageConfig(Config):
  def __init__(self):
    #Default values for storage config
    self.fixedRecordingPath = "~/Videos"
    self.storagePartUUID = "" #UUID of a partition to use
    self.useDedicatedPart = False #Toggle between a fixed path or partition

class RecordingConfig(Config):
  def __init__(self):
    #Default values for recording config
    self.bitRate = 1000000 * 8
    self.width = 1920
    self.height = 1080
    self.duration = 3600 #In seconds

defaultStorageConfig = StorageConfig()
defaultRecordingConfig = RecordingConfig()

def resolvePath(path):
  return os.path.abspath(os.path.expanduser(path))

#Save a config file
#Return True on success
def writeConfig(configPath, configValues):
  configPath = resolvePath(configPath)

  #Convert the config into JSON
  jsonConfig = json.dumps(configValues.toDict(), indent = 4) + "\n"

  #Write the JSON to the config file
  try:
    with open(configPath, "w") as file:
      file.write(jsonConfig)
  except Exception as e:
    print(e)
    print(f"Failed to create config file '{configPath}'")
    return False

  return True

#Read a JSON config file and return an initialised Config()
#Missing keys will have default values filled in, and extra keys will be removed
#Return None on failure
def readConfig(configPath, defaultConfig):
  configPath = resolvePath(configPath)

  #Read the config file
  jsonFileContent = None
  try:
    with open(configPath, "r") as file:
      jsonFileContent = file.read()
  except Exception as e:
    print(e)
    print(f"Failed to read config file '{configPath}'")
    return None

  #Parse the JSON config file
  loadedConfig = json.loads(jsonFileContent)
  configChanges = False

  #Use default values for missing keys
  defaultConfigDict = defaultConfig.toDict()
  for key in defaultConfigDict:
    if key not in loadedConfig:
      loadedConfig[key] = defaultConfigDict[key]
      configChanges = True

  #Find extra keys
  removedKeys = []
  for key in loadedConfig:
    if key not in defaultConfigDict:
      removedKeys.append(key)
      configChanges = True

  #Remove extra keys
  for key in removedKeys:
    del loadedConfig[key]

  #Replace the config if changes were made
  configValues = Config().fromDict(loadedConfig)
  writeConfig(configPath, configValues)

  return configValues

#Ensure the config file exists, using default values if missing
#Return True on success
def ensureConfig(configPath, defaultConfig):
  configPath = resolvePath(configPath)

  #Return early if the path is a file
  if os.path.isfile(configPath):
    return True

  #Fail if the path exists but wasn't a file
  if os.path.exists(configPath):
    print(f"'{configPath}' exists and isn't a config file")
    return False

  #Create the config file with default values
  return writeConfig(configPath, defaultConfig)
