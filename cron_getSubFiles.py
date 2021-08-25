import os
import glob
import shutil
import constants
import datetime

# log root directory 
originalLogDir = constants.ORIGINAL_LOG_DIR

# backup log directory
backupLogDir = constants.BACKUP_LOG_DIR


#Given a device directory and target append file name,
#go inside the device directory and concat all small log files.
def GetSubFiles(dir):
    devBackupPath = os.path.join(backupLogDir, dir[2:len(dir)])
    currDir = os.getcwd()
    os.chdir(dir)
    
    #LogFiles = os.listdir()
    LogFiles = glob.glob("*_log.txt")
    if (len(LogFiles) > 0):
        LogFiles.sort(reverse=False)
        print(LogFiles)
        for logFile in LogFiles:
            shutil.copyfile(logFile, os.path.join(devBackupPath, logFile))        
    os.chdir(currDir)

def main():
	starttime = datetime.datetime.now()
	print( starttime + ": start getting sub files from vgc2" )
    # print("")
    os.chdir(originalLogDir)
    deviceDirs = glob.glob("./*")
    
    #Only get the device directories which are expected to be unique IDs (32char long)
    for dir in deviceDirs:
        if (len(dir) == 34):
            # print (dir);
            GetSubFiles(dir)
	endtime = datetime.datetime.now()
	print( endtime + ": end getting sub files from vgc2" )
    


if __name__ == "__main__":
    main()