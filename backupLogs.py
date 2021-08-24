import os
import glob
import shutil
import constants

# log root directory 
originalLogDir = constants.ORIGINAL_LOG_DIR

# backup log directory
backupLogDir = constants.BACKUP_LOG_DIR

def backupDeviceLogs(dir):
    currDir = os.getcwd();
    os.chdir(dir);

    logFile = glob.glob("Logs.txt")
    configFile = glob.glob("dev.conf")

    # dev folder backup
    devBackupPath = os.path.join(backupLogDir, dir[2:len(dir)])
    print(devBackupPath)
    if not os.path.exists(devBackupPath):
        os.mkdir(devBackupPath)

    if (len(configFile) > 0):
    	shutil.copyfile(configFile[0], os.path.join(devBackupPath, configFile[0]))

    if (len(logFile) > 0):
	    shutil.copyfile(logFile[0], os.path.join(devBackupPath, logFile[0]))


    os.chdir(currDir);

def main():
    # print("")
    os.chdir(originalLogDir)
    deviceDirs = glob.glob("./*")
    
    #Only get the device directories which are expected to be unique IDs (32char long)
    for dir in deviceDirs:
        if (len(dir) == 34):
            # print (dir);
            backupDeviceLogs(dir);
    


if __name__ == "__main__":
    main()