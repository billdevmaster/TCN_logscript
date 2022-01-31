import pymongo
import re
import constants
from datetime import datetime

class Device:
	def __init__(self):
		myclient = pymongo.MongoClient("mongodb://localhost:27017/")
		mydb = myclient["vend-portal"]
		self.vendmachines = mydb["vendmachines"]
		self.machineUID = ''
		self.devName = ''
		self.siteId = ''

	# -------------------------- import config data from logs.txt ----------------------------------------
	def importConfigData(self, dir, machine):
	    with open(dir) as content:
	        lines = content.readlines()
	        start = False
	        config = {}
	        config['machineUID'] = machine[2:len(machine)]
	        self.machineUID = machine[2:len(machine)]
	        config['config'] = {}
	        for line in lines:
	            if "CONF_START" in line:
	                start = True
	                continue
	            if "CONF_END" in line:
	                break
	            if not start:
	                continue

	            item = line.split("=")
	            if "DEV_NAME" in line:
	                self.devName = item[1]
	                self.siteId = self.getSiteIdFromDevName(self.devName)
	            config['config'][item[0]] = item[1].replace('\n', '')
	        config['siteID'] = self.siteId
	        self.vendmachines.update_one({'machineUID' : config['machineUID']}, {'$set': config}, True)

	def getSiteIdFromDevName(self, devName):
	    siteId = ""
	    searchSite = re.search("S[0-9]{3,4}", devName)
	    searchSiteFromD = re.search("D[0-9]{3,4}", devName)
	    searchTest = re.search("TEST", devName)
	    if searchSite:
	        siteId = searchSite.group()
	    if searchTest:
	        siteId = searchTest.group()
	    if searchSiteFromD:
	        siteId = searchSiteFromD.group()
	    if (siteId == ''):
	        siteId = devName
	    return siteId

	def getMachineUID(self):
		return self.machineUID

	def getDevName(self):
		return self.devName

	def getSiteId(self):
		return self.siteId