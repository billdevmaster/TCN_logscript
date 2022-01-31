import pymongo
import re
import constants
from datetime import datetime

class Card:

	def __init__(self):
		myclient = pymongo.MongoClient("mongodb://localhost:27017/")
		mydb = myclient["vend-portal"]
		self.vendmachines = mydb["vendmachines"]
		self.transactions = mydb["transactions"]
		self.products = mydb["products"]
		self.planograms = mydb["planograms"]
		self.cashCoinStatusModel = mydb["coinTubeStatus"]

		self.machineUID = ''
		self.devName = ''
		self.siteId = ''

		self.cardTransactionState = {
		    "start": False,
		    "status": True,
		    "time": "",
		    "failReason": "",
		    "preAuth" : {
		        "status" : False,
		        "amount" : 0
		    },
		    "product" : {
		        "selectedItem" : "none",
		        "price" : 0
		    },
		    "vendCom" : False,
		    "sessionCom" : False,
		    "cardType": "unknown",
		    "fee": 0,
		    "refund": 0,
		    "terminalID": "",
		    "cardNum": "",
		    "line_no": -1,
		    "startLineNumber": -1,
		    "endLineNumber": -1
		}
	
	def setParams(self, cardTransactionState):
		self.cardTransactionState = cardTransactionState

	def setDevice(self, machineUID, devName, siteId):
		self.machineUID = machineUID
		self.devName = devName
		self.siteId = siteId

	def formatCardTransaction(self, line_no):
	    self.cardTransactionState = {
	        "start": False,
	        "status": True,
	        "time": "",
	        "failReason": "",
	        "preAuth" : {
	            "status" : False,
	            "amount" : 0
	        },
	        "product" : {
	            "selectedItem" : "none",
	            "price" : 0
	        },
	        "vendCom" : False,
	        "sessionCom" : False,
	        "cardType": "unknown",
	        "fee": 0,
	        "refund": 0,
	        "terminalID": "",
	        "cardNum": "",
	        "line_no": line_no,
	        "startLineNumber": -1,
	        "endLineNumber": -1
	    }

	def checkTransaction(self, line, time, line_no):
	    if constants.CARD_TANSACTION_START in line:
	        self.formatCardTransaction(line_no)
	        self.cardTransactionState['start'] = True
	        self.cardTransactionState['line_no'] = line_no
	        self.cardTransactionState['startLineNumber'] = line_no

	    # --------- pre auth--------
	    # card pre auth ok
	    if constants.CARD_PRE_AUTH_OK in line and self.cardTransactionState['start']:
	        self.cardTransactionState['line_no'] = line_no
	        self.cardTransactionState['preAuth']['status'] = True
	        preAuthAmnt = re.search(constants.CARD_PRE_AUTH_AMOUNT_PATTERN, line)
	        if preAuthAmnt:
	            self.cardTransactionState['preAuth']['amount'] = float(preAuthAmnt.group(1))
	        else:
	            self.cardTransactionState['preAuth']['amount'] = 0
	    # card pre auth fail
	    if any(x in line for x in constants.CARD_PRE_AUTH_FAIL) and self.cardTransactionState['start']:
	        self.cardTransactionState['line_no'] = line_no
	        self.cardTransactionState['time'] = time
	        self.cardTransactionState['failReason'] = constants.CARD_FAIL_REASON['PRE_AUTH_FAIL'] + " line:" + line
	        if (self.cardTransactionState['startLineNumber'] == -1):
	            self.cardTransactionState['startLineNumber'] = line_no
	        self.cardTransactionState['endLineNumber'] = line_no
	        self.setCardTransactionResult("failed", line_no)
	            
	    # -------- end pre auth ------------

	    # ------------ product ---------------
	    if constants.CARD_SELECT_ITEM in line and self.cardTransactionState['start']:
	        self.cardTransactionState['line_no'] = line_no
	        selectedItem = re.search(constants.CARD_SELECTED_ITEM_PATTERN, line)
	        if selectedItem:
	            self.cardTransactionState['product']['selectedItem'] = selectedItem.group(1)
	        itemPrice = re.search(constants.ITEM_PRICE_PATTERN, line)
	        if itemPrice:
	            self.cardTransactionState['product']['price'] = round(float(itemPrice.group(1)) * 100, 2)

	    if constants.CARD_NO_ITEM_SELECTED in line and self.cardTransactionState['start']:
	        self.cardTransactionState['line_no'] = line_no
	        self.cardTransactionState['time'] = time
	        self.cardTransactionState['failReason'] = constants.CARD_FAIL_REASON['NO_ITEM_SELECTED'] + " line: " + line

	    # ------------ end product ---------------

	    # card vend cancel
	    if constants.CARD_VEND_FAIL_VOID in line and self.cardTransactionState['start']:
	        self.cardTransactionState['line_no'] = line_no
	        self.cardTransactionState['time'] = time
	        self.cardTransactionState['failReason'] = constants.CARD_FAIL_REASON['VEND_FAIL_SEND_VOID'] + " line: " + line
	        self.cardTransactionState['refund'] = self.cardTransactionState['preAuth']['amount']
	        self.cardTransactionState['vendCom'] = False


	    if constants.CARD_VEND_FAIL_CANCEL in line and self.cardTransactionState['start']:
	        self.cardTransactionState['line_no'] = line_no
	        self.cardTransactionState['time'] = time
	        self.cardTransactionState['failReason'] = constants.CARD_FAIL_REASON['VEND_FAIL_SEND_CANCEL'] + " line: " + line
	        self.cardTransactionState['refund'] = self.cardTransactionState['preAuth']['amount']
	        self.cardTransactionState['vendCom'] = False
	        

	    # end card vend cancel

	    if constants.CARD_VEND_SUCCESS in line and self.cardTransactionState['start']:
	        self.cardTransactionState['line_no'] = line_no
	        self.cardTransactionState['vendCom'] = True

	    if constants.CARD_SESSION_COM in line and self.cardTransactionState['start'] and self.cardTransactionState['vendCom']:
	        self.cardTransactionState['line_no'] = line_no
	        self.cardTransactionState['sessionCom'] = True
	    # card transaction success
	     
	    if constants.CARD_TXN_AUTH_CANCEL in line and not self.cardTransactionState['preAuth']['status']:
	        self.cardTransactionState['line_no'] = line_no
	        self.cardTransactionState['time'] = time
	        self.cardTransactionState['failReason'] = constants.CARD_FAIL_REASON['TXN_AUTH_CANCEL'] + " line: " + line
	        if (self.cardTransactionState['startLineNumber'] == -1):
	            self.cardTransactionState['startLineNumber'] = line_no
	        self.cardTransactionState['endLineNumber'] = line_no
	        self.setCardTransactionResult("failed", line_no)          
	    # end card transaction success

	    # card transaction get1
	    if constants.CARD_GET1 in line and self.cardTransactionState['start'] and self.cardTransactionState['preAuth']['status']:
	        self.cardTransactionState['line_no'] = line_no
	        get1Res = re.search(constants.CARD_GET1_VALUE_PATTERN, line)
	        self.cardTransactionState['time'] = time
	        self.cardTransactionState['endLineNumber'] = line_no
	        if get1Res and (len(get1Res.group(1)) > 1):
	            dataArray = get1Res.group(1).split(',')
	            self.cardTransactionState['cardType'] = dataArray[1]
	            if (len(dataArray) >= 3):
	                self.cardTransactionState['fee'] = int(dataArray[3]) - int(dataArray[2])
	            else: 
	                self.cardTransactionState['fee'] = 0
	            if (len(dataArray) >= 23):
	                self.cardTransactionState['terminalID'] = dataArray[23]
	            else:
	                self.cardTransactionState['terminalID'] = "unknown"

	            if (len(dataArray) >= 16):
	                self.cardTransactionState['cardNum'] = dataArray[16]
	            else:
	                self.cardTransactionState['cardNum'] = "unknown"

	            if (len(dataArray) >= 14 and dataArray[14] == 'COMP'):
	                self.setCardTransactionResult("success", line_no)
	            elif (len(dataArray) >= 14 and dataArray[14] == 'VOID'):
	                # self.cardTransactionState['failReason'] = "TXN GET1: Auth: VOID"
	                self.cardTransactionState['refund'] = dataArray[3]
	                self.setCardTransactionResult("failed", line_no)

	    # end card transaction get1

	def setCardTransactionResult (self, type, line_no):
	    data = {
	        "machineUID" : self.machineUID,
	        "devName" : self.devName,
	        "siteID" : self.siteId,
	        "type" : "CARD",
	        "subType" : self.cardTransactionState['cardType'],
	        "status" : type,
	        "time" : self.cardTransactionState['time'],
	        "product" : self.getProductIdFromSelectedItem(self.cardTransactionState['product']['selectedItem'], self.cardTransactionState['product']['price']),
	        # "price" : self.cardTransactionState['product']['price'],
	        "selectedItem": self.cardTransactionState['product']['selectedItem'],
	        "fee" : self.cardTransactionState['fee'],
	        "refund" : self.cardTransactionState['refund'],
	        "failReason" : self.cardTransactionState['failReason'],
	        "startLineNumber" : self.cardTransactionState['startLineNumber'],
	        "endLineNumber" : self.cardTransactionState['endLineNumber'],
	        "preAuth" : self.cardTransactionState['preAuth']['amount'],
	        "cardNumber" : self.cardTransactionState['cardNum'],
	    }
	    self.transactions.update_one({'machineUID' : data['machineUID'], 'time': data['time']}, {'$set': data}, True)
	    self.formatCardTransaction(line_no)

	def getProductIdFromSelectedItem(self, selectedItem, price):
	    result = {'productID': 'unknown', 'aisleNum': selectedItem.strip(), 'price': price}
	    productId = ''
	    planogram = self.planograms.find_one({ 'machineUID': self.machineUID })
	    if planogram:
	        for row in planogram['rows']:
	            for aisle in row['aisles']:
	                if selectedItem.strip(' ').isdigit()  and ( aisle['aisleNum'] == int(selectedItem.strip(' ')) ):
	                    if 'productId' in aisle.keys():
	                        result['productID'] = aisle['productId']
	    return result

