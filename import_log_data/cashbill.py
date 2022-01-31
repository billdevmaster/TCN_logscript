import pymongo
import re
import constants
from datetime import datetime

class CashBill:
	myclient = pymongo.MongoClient("mongodb://localhost:27017/")
	mydb = myclient["vend-portal"]
	vendmachines = mydb["vendmachines"]
	transactions = mydb["transactions"]
	products = mydb["products"]
	planograms = mydb["planograms"]
	cashCoinStatusModel = mydb["coinTubeStatus"]

	def setParams():
