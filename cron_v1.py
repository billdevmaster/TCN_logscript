import os
import glob
import pymongo
import re
import constants
import ast

from datetime import datetime
from import_config_data.device import Device
from import_log_data.card import Card

ProjectDirName = constants.BACKUP_LOG_DIR
DeviceInstance = Device()
CardInstance = Card()

def ImportLogData(dir):
    global lastLineNum
    with open(dir) as content:
        for line_no, line in enumerate(content):
            # get current time
            if re.match("[0-9]{4}\-[0-9]{2}\-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}:[0-9]{3}", line[0:23]):
                time = datetime.strptime(line[0:23], '%Y-%m-%d %H:%M:%S:%f')

            CardInstance.checkTransaction(line, time, line_no + 1)
            
            lastLineNum = int(line_no + 1)

def importMachineData(dir):
    currDir = os.getcwd()
    os.chdir(dir)
    subDirs = glob.glob("./*")
    path = os.path.join(constants.BACKUP_LOG_DIR, dir, "stateConfig.conf")
    if not os.path.exists(path):
        open(path, 'x')

    for subDir in subDirs:
        if (subDir[2:len(subDir)] == 'dev.conf'):
            DeviceInstance.importConfigData(subDir, dir)
            CardInstance.setDevice(DeviceInstance.getMachineUID(), DeviceInstance.getDevName(), DeviceInstance.getSiteId())
        if (subDir[2:len(subDir)] == 'Logs.txt'):
            ImportLogData(subDir)
    # ExportStateData(path)
    os.chdir(currDir);

def main():
	os.chdir(ProjectDirName)
	deviceDirs = glob.glob("./*")

	for dir in deviceDirs:
		if (len(dir) == 34):
			if "1A1E62455337433231202020FF0D1B04" in dir:
            #     print(dir)
				importMachineData(dir);

if __name__ == "__main__":
    main()