import os
import glob
import pymongo
import re
import constants
from datetime import datetime

# constants
LOGS_TYPE = {
    "failCommunicationToPaymentServer" : "FAIL_COMMUNCATION_TO_PAYMENT_SERVER",
    "powerLost" : "POWER_LOST",
    "powerRestore" : "POWER_RESTORE",
}
# end constants

# Mongo Config
myclient = pymongo.MongoClient("mongodb://localhost:27017/")
mydb = myclient["vend-portal"]
vendmachines = mydb["vendmachines"]
transactions = mydb["transactions"]
products = mydb["products"]
planograms = mydb["planograms"]

#Project root directory name:
ProjectDirName = constants.BACKUP_LOG_DIR
machineUID = ""
devName = ""
siteId = ""

#Append file name:
AppendedLogFileName = "Logs.txt"

# Transaction data model
lastLineNum = -1
# ---------------------------------- card config -------------------------------------
cardTransactionState = {
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

# end card pre auth config
# ------------------------------- end card config --------------------------------------

# ------------------------------- cash coin config -------------------------------------
coinTubeLevelFormat = [
    0.00, 0.10, 0.20, 0.50, 0.00, 2.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00
]

cashCoinTransactionState = {
    "start" : False,
    "sessionCom" : False,
    "afterVend" : False,
    "status" : False,
    "time" : False,
    "initialTubeStatus" : "",
    "afterVendTubeStatus" : "",
    "afterPayoutTubeStatus" : "",
    "product" : {
        "selectedItem": "none",
        "price": 0,
    },
    "amount" : False,
    "failReason" : "",
    "routingCoins": [],
    "cashBoxCoins": [],
    "totalVendedPrice": 0,
    "totalRoutedPrice": 0,
    "totalRefundPrice": 0,
    "line_no": -1,
    "startLineNumber": -1,
    "currentTubeStatus" : "",
    "escrowRequest" : False,
}
# ---------------------------- end cash coin config ------------------------------------

# ------------------------------- cash coin config -------------------------------------
billValueLevelFormat = [
    0.00, 0.10, 0.20, 0.50, 0.00, 2.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00
]
cashBillTransactionState = {
    "start" : False,
    "stacked" : False,
    "status" : "",
    "requestNum" : 0,
    "time" : "",
    "product" : {
        "selectedItem": "none",
        "price": 0
    },
    "sessionCom" : False,
    "payRefund" : False,
    "initialTubeStatus" : "",
    "afterVendTubeStatus" : "",
    "afterRefundTubeStatus" : "",
    "totalVendedPrice": 0,
    "totalRoutedPrice": 0,
    "totalRefundPrice": 0,
    "billLevel": "none",
    "line_no": -1,
    "startLineNumber": -1,
    "currentTubeStatus": "",
    "escrowRequest": False,
}
# ---------------------------- end cash coin config ------------------------------------

# ------------------------------- check communication with card server --------------------------------------
failCommunicationToPaymentServer = "CMV300: Giving up sending Obj: "
# ------------------------------- end check communication with card server --------------------------------------

# -------------------------- import config data from logs.txt ----------------------------------------
def ImportConfigData(dir, machine):
    with open(dir) as content:
        lines = content.readlines()
        start = False
        config = {}
        config['machineUID'] = machine[2:len(machine)]
        global machineUID
        machineUID = machine[2:len(machine)]
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
                global devName
                global siteId
                devName = item[1]
                siteId = getSiteIdFromDevName(devName)
            config['config'][item[0]] = item[1]

        config['siteID'] = siteId
        vendmachines.update({'machineUID' : config['machineUID']}, config, True)

def getSiteIdFromDevName(devName):
    siteId = ""
    # print(devName)
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

# get productId from product collection using selectedItem.
def getProductIdFromSelectedItem(selectedItem, price):
    result = {'productID': 'unknown', 'aisleNum': selectedItem.strip(), 'price': price}
    productId = ''
    planogram = planograms.find_one({ 'machineUID': machineUID })
    # print(selectedItem * 1)
    if planogram:
        for row in planogram['rows']:
            for aisle in row['aisles']:
                if selectedItem.strip(' ').isdigit()  and ( aisle['aisleNum'] == int(selectedItem.strip(' ')) ):
                    if 'productId' in aisle.keys():
                        result['productID'] = aisle['productId']
                        # print(aisle['productId'])
    return result

def calculateTubeLevelFromStatus(tubeStatus):
    statusArray = tubeStatus.split(" ")
    totalPrice = 0
    index = 0
    while index < len(statusArray) - 1:
        if index < len(coinTubeLevelFormat):
            totalPrice += coinTubeLevelFormat[index] * 100 * ( int(statusArray[index]) ) 
        index += 1
    return totalPrice

def getTubeLevelBefore(type):
    tubeLevel = 0
    if (type == 'coin'):
        tubeLevel = calculateTubeLevelFromStatus(cashCoinTransactionState['initialTubeStatus'])
    else:
        tubeLevel = calculateTubeLevelFromStatus(cashBillTransactionState['initialTubeStatus'])
    return tubeLevel

def getTubeLevelAfter(type):
    tubeLevel = 0
    if ( type == 'coin' ):
        if ( cashCoinTransactionState['afterPayoutTubeStatus'] != '' ):
            tubeLevel = calculateTubeLevelFromStatus( cashCoinTransactionState['afterPayoutTubeStatus'] )
        else:
            if ( cashCoinTransactionState['afterVendTubeStatus'] != '' ):
                tubeLevel = calculateTubeLevelFromStatus( cashCoinTransactionState['afterVendTubeStatus'] )
            else:
                tubeLevel = calculateTubeLevelFromStatus( cashCoinTransactionState['initialTubeStatus'] )
    else:
        if ( cashBillTransactionState['afterRefundTubeStatus'] != '' ):
            tubeLevel = calculateTubeLevelFromStatus( cashBillTransactionState['afterRefundTubeStatus'] )
        else:
            tubeLevel = calculateTubeLevelFromStatus( cashBillTransactionState['initialTubeStatus'] )
    return tubeLevel
# ---------------------------import log data from logs.txt ------------------------------------------
def ImportLogData(dir):
    global lastLineNum
    with open(dir) as content:
        for line_no, line in enumerate(content):
            # get current time
            if re.match("[0-9]{4}\-[0-9]{2}\-[0-9]{2}\ [0-9]{2}:[0-9]{2}:[0-9]{2}:[0-9]{3}", line[0:23]):
                time = datetime.strptime(line[0:23], '%Y-%m-%d %H:%M:%S:%f')
            # end get current time
            setBillValueLevelFormat(line)
            setCoinTubeLevelFormat(line)
            checkCardTransaction(line, time, line_no + 1)
            # checkCommunicationToPaymentServer(line, time)
            checkCashCoinTransaction(line, time, line_no + 1)
            checkCashBillTransaction(line, time, line_no + 1)
            lastLineNum = int(line_no + 1)

# ----------------------------card log analyse--------------------------------
def formatCardTransaction(line_no):
    global cardTransactionState

    cardTransactionState = {
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
    # print(cardTransactionState['start'])

def checkCardTransaction(line, time, line_no):
    global cardTransactionState
    # card Transaction start

    if constants.CARD_TANSACTION_START in line:
        formatCardTransaction(line_no)
        cardTransactionState['start'] = True
        cardTransactionState['line_no'] = line_no
        cardTransactionState['startLineNumber'] = line_no

    # --------- pre auth--------
    # card pre auth ok
    if constants.CARD_PRE_AUTH_OK in line and cardTransactionState['start']:
        cardTransactionState['line_no'] = line_no
        cardTransactionState['preAuth']['status'] = True
        preAuthAmnt = re.search(constants.CARD_PRE_AUTH_AMOUNT_PATTERN, line)
        if preAuthAmnt:
            cardTransactionState['preAuth']['amount'] = float(preAuthAmnt.group(1))
        else:
            cardTransactionState['preAuth']['amount'] = 0
    # card pre auth fail
    if any(x in line for x in constants.CARD_PRE_AUTH_FAIL) and cardTransactionState['start']:
        cardTransactionState['line_no'] = line_no
        cardTransactionState['time'] = time
        cardTransactionState['failReason'] = constants.CARD_FAIL_REASON['PRE_AUTH_FAIL'] + " line:" + line
        if (cardTransactionState['startLineNumber'] == -1):
            cardTransactionState['startLineNumber'] = line_no
        cardTransactionState['endLineNumber'] = line_no
        setCardTransactionResult("failed", line_no)
            
    # -------- end pre auth ------------

    # ------------ product ---------------
    if constants.CARD_SELECT_ITEM in line and cardTransactionState['start']:
        cardTransactionState['line_no'] = line_no
        selectedItem = re.search(constants.CARD_SELECTED_ITEM_PATTERN, line)
        if selectedItem:
            cardTransactionState['product']['selectedItem'] = selectedItem.group(1)
        itemPrice = re.search(constants.ITEM_PRICE_PATTERN, line)
        if itemPrice:
            cardTransactionState['product']['price'] = round(float(itemPrice.group(1)) * 100, 2)

    if constants.CARD_NO_ITEM_SELECTED in line and cardTransactionState['start']:
        cardTransactionState['line_no'] = line_no
        cardTransactionState['time'] = time
        cardTransactionState['failReason'] = constants.CARD_FAIL_REASON['NO_ITEM_SELECTED'] + " line: " + line

    # ------------ end product ---------------

    # card vend cancel
    if constants.CARD_VEND_FAIL_VOID in line and cardTransactionState['start']:
        cardTransactionState['line_no'] = line_no
        cardTransactionState['time'] = time
        cardTransactionState['failReason'] = constants.CARD_FAIL_REASON['VEND_FAIL_SEND_VOID'] + " line: " + line
        cardTransactionState['refund'] = cardTransactionState['preAuth']['amount']
        cardTransactionState['vendCom'] = False


    if constants.CARD_VEND_FAIL_CANCEL in line and cardTransactionState['start']:
        cardTransactionState['line_no'] = line_no
        cardTransactionState['time'] = time
        cardTransactionState['failReason'] = constants.CARD_FAIL_REASON['VEND_FAIL_SEND_CANCEL'] + " line: " + line
        cardTransactionState['refund'] = cardTransactionState['preAuth']['amount']
        cardTransactionState['vendCom'] = False
        

    # end card vend cancel

    if constants.CARD_VEND_SUCCESS in line and cardTransactionState['start']:
        cardTransactionState['line_no'] = line_no
        cardTransactionState['vendCom'] = True

    if constants.CARD_SESSION_COM in line and cardTransactionState['start'] and cardTransactionState['vendCom']:
        cardTransactionState['line_no'] = line_no
        cardTransactionState['sessionCom'] = True
    # card transaction success
     
    if constants.CARD_TXN_AUTH_CANCEL in line and not cardTransactionState['preAuth']['status']:
        cardTransactionState['line_no'] = line_no
        cardTransactionState['time'] = time
        cardTransactionState['failReason'] = constants.CARD_FAIL_REASON['TXN_AUTH_CANCEL'] + " line: " + line
        if (cardTransactionState['startLineNumber'] == -1):
            cardTransactionState['startLineNumber'] = line_no
        cardTransactionState['endLineNumber'] = line_no
        setCardTransactionResult("failed", line_no)          
    # end card transaction success

    # card transaction get1
    if constants.CARD_GET1 in line and cardTransactionState['start'] and cardTransactionState['preAuth']['status']:
        cardTransactionState['line_no'] = line_no
        get1Res = re.search(constants.CARD_GET1_VALUE_PATTERN, line)
        cardTransactionState['time'] = time
        cardTransactionState['endLineNumber'] = line_no
        if get1Res and (len(get1Res.group(1)) > 1):
            dataArray = get1Res.group(1).split(',')
            cardTransactionState['cardType'] = dataArray[1]
            if (len(dataArray) >= 3):
                cardTransactionState['fee'] = int(dataArray[3]) - int(dataArray[2])
            else: 
                cardTransactionState['fee'] = 0
            # print(len(dataArray))
            # print(line_no)
            if (len(dataArray) >= 23):
                cardTransactionState['terminalID'] = dataArray[23]
            else:
                cardTransactionState['terminalID'] = "unknown"

            if (len(dataArray) >= 16):
                cardTransactionState['cardNum'] = dataArray[16]
            else:
                cardTransactionState['cardNum'] = "unknown"

            if (len(dataArray) >= 14 and dataArray[14] == 'COMP'):
                setCardTransactionResult("success", line_no)
            elif (len(dataArray) >= 14 and dataArray[14] == 'VOID'):
                # cardTransactionState['failReason'] = "TXN GET1: Auth: VOID"
                cardTransactionState['refund'] = dataArray[3]
                setCardTransactionResult("failed", line_no)

    # end card transaction get1

def setCardTransactionResult (type, line_no):
    global cardTransactionState

    data = {
        "machineUID" : machineUID,
        "devName" : devName,
        "siteID" : siteId,
        "type" : "CARD",
        "subType" : cardTransactionState['cardType'],
        "status" : type,
        "time" : cardTransactionState['time'],
        "product" : getProductIdFromSelectedItem(cardTransactionState['product']['selectedItem'], cardTransactionState['product']['price']),
        # "price" : cardTransactionState['product']['price'],
        "fee" : cardTransactionState['fee'],
        "refund" : cardTransactionState['refund'],
        "failReason" : cardTransactionState['failReason'],
        "startLineNumber" : cardTransactionState['startLineNumber'],
        "endLineNumber" : cardTransactionState['endLineNumber'],
        "preAuth" : cardTransactionState['preAuth']['amount'],
        "cardNumber" : cardTransactionState['cardNum'],
    }
    transactions.update({'machineUID' : data['machineUID'], 'time': data['time']}, data, True)
    # print(cardTransactionState)
    formatCardTransaction(line_no)
# ----------------------------------end card-----------------------------

# check communication to payment server
def checkCommunicationToPaymentServer(line, time):
    if failCommunicationToPaymentServer in line:
        data = {
            "time": time,
            "logType": LOGS_TYPE['failCommunicationToPaymentServer'],
            "logText": line
        }
        vendmachines.update({'machineUID': machineUID}, {'$push': {'logs': data}})
# end check communication to payment server

# check power on or off
def checkPower(line, time):
    if "DEV: Power lost" in line:
        data = {
            "time": time,
            "logType": LOGS_TYPE['powerLost'],
            "logText": line
        }
        vendmachines.update({'machineUID': machineUID}, {'$push': {'logs': data}})
    if "DEV: Power restored" in line:
        data = {
            "time": time,
            "logType": LOGS_TYPE['powerRestore'],
            "logText": line
        }
        vendmachines.update({'machineUID': machineUID}, {'$push': {'logs': data}})
# end check power on or off

# ---------------------check cash transaction---------------------------
def setCoinTubeLevelFormat(line):
    global coinTubeLevelFormat
    array = []
    if constants.CASH_COIN_CONFIG in line:
        values = re.search(constants.CASH_CONFIG_PATTERN, line)
        if values:
            arr = values.group(1).split(" ")
            for item in arr:
                if item != '':
                    value = float(item)
                    array.insert(len(array), value)

    for index, line in enumerate(array):
        coinTubeLevelFormat[index] = array[index]

def checkCashCoinTransaction(line, time, line_no):
    global cashCoinTransactionState
    if constants.CASH_COIN_TUBE_LEVEL in line and not cashCoinTransactionState['start']:
        initialTubeStatus = re.search(constants.CASH_COIN_TUBE_LEVEL_PATTERN, line)
        if initialTubeStatus:
            cashCoinTransactionState['initialTubeStatus'] = initialTubeStatus.group(1)

    if (cashCoinTransactionState['initialTubeStatus'] != ""):
        if (constants.CASH_COIN_ROUTING_TUBES in line or constants.CASH_COIN_ROUTING_CASH_BOX in line) and cashCoinTransactionState['sessionCom']:
            # print(cashCoinTransactionState)
            if (cashCoinTransactionState['totalRoutedPrice'] == cashCoinTransactionState['product']['price']):
                setCashCoinTransaction("success", time, line_no)
            elif (cashCoinTransactionState['product']['selectedItem'] == "none"):
                cashCoinTransactionState['failReason'] = constants.CASH_COIN_FAIL_REASON['NO_ITEM_SELECTED']
                setCashCoinTransaction("failed", time, line_no)
            else:
                cashCoinTransactionState['line_no'] = line_no
                formatCashCoinTransaction(cashCoinTransactionState['currentTubeStatus'], line_no)

        # add coin
        if (constants.CASH_COIN_ROUTING_TUBES in line or constants.CASH_COIN_ROUTING_CASH_BOX in line) and not cashCoinTransactionState['start']:
            cashCoinTransactionState['line_no'] = line_no
            cashCoinTransactionState['startLineNumber'] = line_no
            cashCoinTransactionState['start'] = True
        # end add coin

        # calculate coin tube levels:
        if constants.CASH_COIN_ROUTING_TUBES in line and not cashCoinTransactionState['sessionCom']:
            cashCoinTransactionState['line_no'] = line_no
            if (cashCoinTransactionState['currentTubeStatus'] == ""):
                cashCoinTransactionState['currentTubeStatus'] = cashCoinTransactionState['initialTubeStatus']
            tubeLevel = re.search(constants.CASH_COIN_ROUTING_PRICE, line)
            if tubeLevel:
                numOfCoin = re.search(constants.CASH_COIN_ROUTING_LEVEL, line)
                if numOfCoin:
                    cashCoinTransactionState['routingCoins'].insert(0, numOfCoin.group(1))
                    if (tubeLevel.group(1) == '0'):
                        tubeLevelArray = cashCoinTransactionState['currentTubeStatus'].split(" ")
                        cashCoinTransactionState['currentTubeStatus'] = ""
                        for coin in tubeLevelArray:
                            if coin.isdigit():
                                if (int(numOfCoin.group(1)) == (int(coin) + 1)):
                                    index = tubeLevelArray.index(str(coin))
                                    cashCoinTransactionState['totalRoutedPrice'] += coinTubeLevelFormat[index] * 100
                                    coin = numOfCoin.group(1)
                            cashCoinTransactionState['currentTubeStatus'] += coin + " "
                    else:
                        cashCoinTransactionState['totalRoutedPrice'] += float(tubeLevel.group(1)) * 100
                        index = coinTubeLevelFormat.index(float(tubeLevel.group(1)))
                        tubeLevelArray = cashCoinTransactionState['currentTubeStatus'].split(" ")
                     
                        numOfCoin = re.search(constants.CASH_COIN_ROUTING_LEVEL, line)
                        cashCoinTransactionState['currentTubeStatus'] = ""
                        if numOfCoin:
                            tubeLevelArray[index] = numOfCoin.group(1)
                            for coin in tubeLevelArray:
                                if coin.isdigit():
                                    cashCoinTransactionState['currentTubeStatus'] += str(coin) + " "

        if constants.CASH_COIN_ROUTING_CASH_BOX in line and not cashCoinTransactionState['sessionCom']:
            if (cashCoinTransactionState['currentTubeStatus'] == ""):
                cashCoinTransactionState['currentTubeStatus'] = cashCoinTransactionState['initialTubeStatus']
            tubeLevel = re.search(constants.CASH_COIN_CASHBOX_PRICE, line)
            if tubeLevel:
                numOfCoin = re.search(constants.CASH_COIN_ROUTING_LEVEL, line)
                if numOfCoin:
                    
                    cashCoinTransactionState['cashBoxCoins'].insert(len(cashCoinTransactionState['cashBoxCoins']), numOfCoin.group(1))
                    if (tubeLevel.group(1) == '0'):
                        tubeLevelArray = cashCoinTransactionState['currentTubeStatus'].split(" ")
                        for coin in tubeLevelArray:
                            if coin.isdigit():
                                if (int(numOfCoin.group(1)) == int(coin)):
                                    index = tubeLevelArray.index(str(coin))
                                    cashCoinTransactionState['totalRoutedPrice'] += coinTubeLevelFormat[index] * 100
                    # if (line_no >= 11764) and (line_no <= 11764):
                    #     print(cashCoinTransactionState['totalRoutedPrice'])
                    #     print(line_no)
                    else:
                        cashCoinTransactionState['totalRoutedPrice'] += float(tubeLevel.group(1)) * 100
            
        if constants.CASH_SELECT_ITEM in line and cashCoinTransactionState['start'] and not cashCoinTransactionState['sessionCom']:
            cashCoinTransactionState['line_no'] = line_no
            product = {}
            selectedItem = re.search(constants.CASH_SELECTED_ITEM_PATTERN, line)
            if selectedItem:
                product['selectedItem'] = selectedItem.group(1)
            price = re.search(constants.ITEM_PRICE_PATTERN, line)
            if price:
                product['price'] = round(float(price.group(1)) * 100, 2)
            cashCoinTransactionState['product'] = product

        if constants.CASH_SESSION_COMPLETE in line and cashCoinTransactionState['start'] and not cashCoinTransactionState['sessionCom']:
            cashCoinTransactionState['line_no'] = line_no
            cashCoinTransactionState['sessionCom'] = True
            if (cashCoinTransactionState['totalRoutedPrice'] == cashCoinTransactionState['product']['price']):
                setCashCoinTransaction("success", time, line_no)

        if constants.CASH_COIN_ESCROW_REQUEST in line and cashCoinTransactionState['start']:
            cashCoinTransactionState['escrowRequest'] = True

        if constants.CASH_COIN_TUBE_LEVEL in line and cashCoinTransactionState['start'] and not cashCoinTransactionState['afterVend'] and cashCoinTransactionState['sessionCom']:
            if (line_no == (cashCoinTransactionState['line_no'] + 1)):
                cashCoinTransactionState['line_no'] = line_no
                afterVendTubeStatus = re.search(constants.CASH_COIN_TUBE_LEVEL_PATTERN, line)
                if afterVendTubeStatus:
                    cashCoinTransactionState['afterVendTubeStatus'] = afterVendTubeStatus.group(1)
                    cashCoinTransactionState['currentTubeStatus'] = afterVendTubeStatus.group(1)
                    # totalRoutedPriceNew = getRoutedCoinPrice(line_no)
                    # if (totalRoutedPriceNew > 0):
                    #     cashCoinTransactionState['totalRoutedPrice'] = totalRoutedPriceNew

            else:
                if (cashCoinTransactionState['totalRoutedPrice'] == cashCoinTransactionState['product']['price']):
                    setCashCoinTransaction("success", time, line_no)
                if (cashCoinTransactionState['product']['selectedItem'] == "none"):
                    cashCoinTransactionState['failReason'] = constants.CASH_COIN_FAIL_REASON['NO_ITEM_SELECTED']
                    setCashCoinTransaction("failed", time, line_no)
                cashCoinTransactionState['line_no'] = line_no
                formatCashCoinTransaction(cashCoinTransactionState['currentTubeStatus'], line_no)

        if constants.CASH_COIN_TUBE_LEVEL in line and cashCoinTransactionState['start'] and cashCoinTransactionState['escrowRequest'] and not cashCoinTransactionState['afterVend']:

            afterVendTubeStatus = re.search(constants.CASH_COIN_TUBE_LEVEL_PATTERN, line)
            if afterVendTubeStatus:
                cashCoinTransactionState['currentTubeStatus'] = afterVendTubeStatus.group(1)
                cashCoinTransactionState['totalRoutedPrice'] = getRoutedCoinPrice(line_no)

        if constants.CASH_COIN_PAY_OUT in line and cashCoinTransactionState['start']:
            cashCoinTransactionState['line_no'] = line_no
            cashCoinTransactionState['afterVend'] = True

        if constants.CASH_COIN_TUBE_LEVEL in line and cashCoinTransactionState['start'] and cashCoinTransactionState['afterVend']:
            cashCoinTransactionState['line_no'] = line_no
            afterPayoutTubeStatus = re.search(constants.CASH_COIN_TUBE_LEVEL_PATTERN, line)
            if afterPayoutTubeStatus:
                cashCoinTransactionState['afterPayoutTubeStatus'] = afterPayoutTubeStatus.group(1)
                totalRefundPrice = getRefundPrice(line_no)
                
                
                cashCoinTransactionState['currentTubeStatus'] = afterPayoutTubeStatus.group(1)
                if cashCoinTransactionState['sessionCom']:
                    if (totalRefundPrice == (cashCoinTransactionState['totalRoutedPrice'] - cashCoinTransactionState['product']['price'])):
                        setCashCoinTransaction("success", time, line_no)
                    else:
                        # calculate total routed price again using the after vend status and after payout status.
                        if (cashCoinTransactionState['afterVendTubeStatus'] != ''):
                            cashCoinTransactionState['totalRoutedPrice'] = getRoutedCoinPrice(line_no)
                            if (totalRefundPrice == (cashCoinTransactionState['totalRoutedPrice'] - cashCoinTransactionState['product']['price'])):
                                setCashCoinTransaction("success", time, line_no)
                            else:
                                cashCoinTransactionState['failReason'] = "Price doesn't match"
                                setCashCoinTransaction("failed", time, line_no)    
                        else:
                            cashCoinTransactionState['failReason'] = "Price doesn't match"
                            setCashCoinTransaction("failed", time, line_no)
                elif cashCoinTransactionState['escrowRequest']:
                    if (totalRefundPrice == cashCoinTransactionState['totalRoutedPrice']):
                        cashCoinTransactionState['failReason'] = "Escrow requested, refund all"
                        setCashCoinTransaction("failed", time, line_no)
                    else:
                        cashCoinTransactionState['failReason'] = "Escrow requested, refund not match"
                        setCashCoinTransaction("failed", time, line_no)

def formatCashCoinTransaction(lastTubeStatus = "", line_no = 0):
    global cashCoinTransactionState
    cashCoinTransactionState = {
        "start" : False,
        "sessionCom" : False,
        "afterVend" : False,
        "status" : False,
        "time" : False,
        "initialTubeStatus" : cashCoinTransactionState['currentTubeStatus'],
        "afterVendTubeStatus" : "",
        "afterPayoutTubeStatus" : "",
        "product" : {
            "selectedItem": "none",
            "price": 0,
        },
        "amount" : False,
        "failReason" : "",
        "routingCoins": [],
        "cashBoxCoins": [],
        "line_no": line_no,
        "totalVendedPrice": 0,
        "totalRoutedPrice": 0,
        "totalRefundPrice": 0,
        "startLineNumber": -1,
        "currentTubeStatus" : "",
        "escrowRequest" : False,
    }

def getRoutedCoinPrice(line_no):
    totalRoutedCoinPrice = 0
    tubeLevelArray = cashCoinTransactionState['afterVendTubeStatus'].split(" ")
    initialTubeLevelArray = cashCoinTransactionState['initialTubeStatus'].split(" ")

    enable = False
    for coin in cashCoinTransactionState['cashBoxCoins']:
        if str(coin) in tubeLevelArray:
            index = tubeLevelArray.index(str(coin))
            totalRoutedCoinPrice += coinTubeLevelFormat[index] * 100
    for coin in cashCoinTransactionState['routingCoins']:
        lastCoinLevel = int(coin);
        if str(lastCoinLevel) in tubeLevelArray:
            index = tubeLevelArray.index(str(lastCoinLevel))
            if (tubeLevelArray[index] != initialTubeLevelArray[index]):
                
                totalRoutedCoinPrice += coinTubeLevelFormat[index] * 100
                tubeLevelArray[index] = str(int(tubeLevelArray[index]) - 1)
    return totalRoutedCoinPrice

def getRoutedCoinPriceFromVendedLevel():
    if cashCoinTransactionState['totalRoutedPrice'] > 0:
        return cashCoinTransactionState['totalRoutedPrice']
    else:
        tubeLevelArray = cashCoinTransactionState['afterVendTubeStatus'].split(" ")
        totalRoutedCoinPrice = 0
        for coin in cashCoinTransactionState['routingCoins']:
            if str(coin) in tubeLevelArray:
                index = tubeLevelArray.index(str(coin))
                tubeLevelArray[index] = str(int(tubeLevelArray[index]) - 1)
                totalRoutedCoinPrice += coinTubeLevelFormat[index] * 100
        return totalRoutedCoinPrice

def getRefundPrice(line_no):
    currentTubeStatus = cashCoinTransactionState['currentTubeStatus'].split(" ")
    payoutTubeLevelArray = cashCoinTransactionState['afterPayoutTubeStatus'].split(" ")
    totalRefundPrice = 0
    index = 0
    # print(cashCoinTransactionState['currentTubeStatus'])
    # print(currentTubeStatus)
    while index < len(currentTubeStatus) - 1:
        if (index < len(payoutTubeLevelArray)):
            if currentTubeStatus[index].isdigit() and payoutTubeLevelArray[index].isdigit():
                totalRefundPrice += float(coinTubeLevelFormat[index]) * 100 * (int(currentTubeStatus[index]) - int(payoutTubeLevelArray[index]))
                    # exit()
        index += 1
    # if (line_no > 420) and (line_no < 429):
    #     print(totalRefundPrice)
    return int(totalRefundPrice)  

def getCashBoxPrice():
    totalPrice = 0
    vendTubeLevelArray = cashCoinTransactionState['afterVendTubeStatus'].split(" ")
    for cashCoin in cashCoinTransactionState['cashBoxCoins']:
        if str(cashCoin) in vendTubeLevelArray:
            index = vendTubeLevelArray.index(str(cashCoin))
            totalPrice += coinTubeLevelFormat[index] * 100

    return totalPrice

def countZeroCashBox():
    count = 0;
    for cashCoin in cashCoinTransactionState['cashBoxCoins']:
        if (cashCoin == '0'):
            count += 1
    return count

def getTotalVendPrice():
    totalVendedPrice = cashCoinTransactionState['product']['price']
    # for item in cashCoinTransactionState['product']:
    #     totalVendedPrice += item['price']

    return totalVendedPrice

def setCashCoinTransaction(type, time, line_no):
    global cashCoinTransactionState
    # if (line_no == 7895):
    #     print(cashCoinTransactionState)
    #     print(cashCoinTransactionState['totalRefundPrice'])
    data = {
        "machineUID" : machineUID,
        "devName" : devName,
        "siteID" : siteId,
        "type" : "CASH", 
        "subType" : "COIN",
        "status" : type,
        "time" : time,
        "product" : getProductIdFromSelectedItem(cashCoinTransactionState['product']['selectedItem'], cashCoinTransactionState['product']['price']),
        "refund" : cashCoinTransactionState['totalRefundPrice'],
        "failReason" : cashCoinTransactionState['failReason'],
        "tubeLevelBefore" : cashCoinTransactionState['initialTubeStatus'],
        "tubeLevelAfter" : cashCoinTransactionState['currentTubeStatus'],
        "cashBoxCoins": cashCoinTransactionState['cashBoxCoins'],
        "routedCoins": cashCoinTransactionState['routingCoins'],
        "startLineNumber" : cashCoinTransactionState['startLineNumber'],
        "endLineNumber" : line_no,
    }
    if (data['product'] != "none"):
        transactions.update({'machineUID' : data['machineUID'], 'time': data['time']}, data, True)
    
    # print(type)
    formatCashCoinTransaction(cashCoinTransactionState['currentTubeStatus'], line_no)
# ---------------------end check cash transaction------------------------------

# --------------------------- check cash bill note ----------------------------
def setBillValueLevelFormat(line):
    global billValueLevelFormat
    array = []
    if "MDBS: BILLV: CONFIG:" in line:
        values = re.search("BillValues\(\$\): (.+?)$", line)
        if values:
            arr = values.group(1).split(" ")
            for item in arr:
                if item != '':
                    value = float(item) * 100
                    array.insert(len(array), value)

    for index, line in enumerate(array):
        billValueLevelFormat[index] = array[index]

def checkCashBillTransaction(line, time, line_no):
    global cashBillTransactionState
    if constants.CASH_COIN_TUBE_LEVEL in line and not cashBillTransactionState['start']:
        initialTubeStatus = re.search(constants.CASH_COIN_TUBE_LEVEL_PATTERN, line)
        if initialTubeStatus:
            cashBillTransactionState['line_no'] = line_no
            cashBillTransactionState['initialTubeStatus'] = initialTubeStatus.group(1)

    if constants.CASH_BILL_ESCROWED in line:
        if cashBillTransactionState['start']:
            cashBillTransactionState = formatcashBillTransaction(cashBillTransactionState['initialTubeStatus'], line_no)
        cashBillTransactionState['start'] = True
        cashBillTransactionState['startLineNumber'] = line_no
        billLevel = re.search("BILLV: Escrowed: (.+?), NumOfBills", line)
        if billLevel:
            cashBillTransactionState['line_no'] = line_no
            cashBillTransactionState['billLevel'] = billLevel.group(1)

    if "MDBS: COINCH: Escrow Request." in line and cashBillTransactionState['start']:
        cashBillTransactionState['line_no'] = line_no
        cashBillTransactionState['requestNum'] += 1

    if "BILLV: Bill Returned: " in line and cashBillTransactionState['start'] and (cashBillTransactionState['requestNum'] > 0):
        cashBillTransactionState['line_no'] = line_no
        setCashBillTransaction("failed", time, "Escrow Requested")

    if "MDBS: BILLV: Stacked: " in line and cashBillTransactionState['start']:
        cashBillTransactionState['line_no'] = line_no
        cashBillTransactionState['stacked'] = True

    if "MDBS: OTHER <= VEND REQUEST Item:" in line and cashBillTransactionState['start'] and cashBillTransactionState['stacked']:
        cashBillTransactionState['line_no'] = line_no
        cashBillTransactionState['product'] = {}
        item = re.search("REQUEST Item: (.+?), Price", line)
        if item:
            cashBillTransactionState['product']['selectedItem'] = item.group(1)
        price = re.search("Price: (.+?)\.$", line)
        if price:
            cashBillTransactionState['product']['price'] = round(float(price.group(1)) * 100, 2)

    if "MDBS: OTHER <= SESSION COMPLETE." in line and cashBillTransactionState['start'] and cashBillTransactionState['stacked']:
        cashBillTransactionState['line_no'] = line_no
        cashBillTransactionState['sessionCom'] = True

    if "MDBS: COINCH: TubeFull:" in line and cashBillTransactionState['start'] and cashBillTransactionState['stacked'] and cashBillTransactionState['sessionCom'] and not cashBillTransactionState['payRefund'] and not cardTransactionState['start']:

        cashBillTransactionState['line_no'] = line_no
        cashBillTransactionState['initialTubeStatus'] = re.search(", TubeStatus: (.+?)\ \.$", line).group(1)

    if "MDBS: COINCH: Payout Status Total:" in line and cashBillTransactionState['sessionCom']:
        cashBillTransactionState['line_no'] = line_no
        cashBillTransactionState['payRefund'] = True
        totalRefundPrice = re.search("MDBS: COINCH: Payout Status Total: (.+?)$", line)
        if totalRefundPrice and (float(totalRefundPrice.group(1)) > 0):
            cashBillTransactionState['totalRefundPrice'] = totalRefundPrice.group(1)

    if "MDBS: COINCH: TubeFull:" in line and cashBillTransactionState['start'] and cashBillTransactionState['stacked'] and cashBillTransactionState['sessionCom'] and cashBillTransactionState['payRefund']:
        cashBillTransactionState['line_no'] = line_no
        cashBillTransactionState['afterRefundTubeStatus'] = re.search(", TubeStatus: (.+?)\ \.$", line).group(1)
        if (cashBillTransactionState['totalRefundPrice'] == 0):
            cashBillTransactionState['totalRefundPrice'] = calculateBillRefundPrice()
        if float(cashBillTransactionState['totalRefundPrice']) + float(cashBillTransactionState['product']['price']) in billValueLevelFormat:
            index = billValueLevelFormat.index(float(cashBillTransactionState['totalRefundPrice']) + float(cashBillTransactionState['product']['price']))
            cashBillTransactionState['billLevel'] = billValueLevelFormat[index]
            if (cashBillTransactionState['product']['selectedItem'] == "none"):
                setCashBillTransaction("failed", time, "No Item selected", line_no)
            else:   
                setCashBillTransaction("success", time, "", line_no)
        elif float(cashBillTransactionState['totalRefundPrice']) in billValueLevelFormat:
            index = billValueLevelFormat.index(float(cashBillTransactionState['totalRefundPrice']))
            cashBillTransactionState['billLevel'] = billValueLevelFormat[index]
            setCashBillTransaction("failed", time, "Totally Refund", line_no)

def formatcashBillTransaction(lastTubeStatus = "", line_no = 0):
    return {
        "start" : False,
        "stacked" : False,
        "status" : "",
        "requestNum" : 0,
        "time" : "",
        "product" : {
            "selectedItem": "none",
            "price": 0
        },
        "sessionCom" : False,
        "payRefund" : False,
        "initialTubeStatus" : lastTubeStatus,
        "afterRefundTubeStatus" : "",
        "totalVendedPrice": 0,
        "totalRoutedPrice": 0,
        "totalRefundPrice": 0,
        "billLevel": "none",
        "line_no": line_no,
        "startLineNumber": -1,
        "currentTubeStatus": ""
    }

def setCashBillTransaction(type, time, failReason = "", line_no = 0):
    global cashBillTransactionState
    
    data = {
        "machineUID" : machineUID,
        "devName" : devName,
        "siteID" : siteId,
        "type" : "CASH", 
        "subType" : "BILL",
        "status" : type,
        "time" : time,
        "product" : getProductIdFromSelectedItem(cashBillTransactionState['product']['selectedItem'], cashBillTransactionState['product']['price']),
        "refund" : cashBillTransactionState['totalRefundPrice'],
        "billLevel" : cashBillTransactionState['billLevel'],
        "failReason": failReason,
        "tubeLevelBefore" : cashBillTransactionState['initialTubeStatus'],
        "tubeLevelAfter" : cashBillTransactionState['afterRefundTubeStatus'],
        "startLineNumber" : cashBillTransactionState['startLineNumber'],
        "endLineNumber" : line_no
    }
    coinTxndata = {
        "machineUID" : machineUID,
        "devName" : devName,
        "siteID" : siteId,
        "type" : "CASH", 
        "subType" : "COIN",
        "status" : type,
        "time" : time,
        "product" : {'productID': 'bankBill', 'aisleNum': 0, 'price': 0},
        "refund" : float(cashBillTransactionState['totalRefundPrice']) * 1,
        "failReason" : failReason,
        "tubeLevelBefore" : cashBillTransactionState['initialTubeStatus'],
        "tubeLevelAfter" : cashBillTransactionState['afterRefundTubeStatus'],
        "cashBoxCoins": [],
        "routedCoins": [],
        "startLineNumber" : cashBillTransactionState['startLineNumber'],
        "endLineNumber" : line_no,
    }
    # print(cashBillTransactionState)
    if (data['product'] != "none"):
        transactions.update({'machineUID' : data['machineUID'], 'time': data['time'], 'type': data['type'], 'subType': data['subType']}, data, True)
        transactions.update({'machineUID' : coinTxndata['machineUID'], 'time': coinTxndata['time'], 'type': coinTxndata['type'], 'subType': coinTxndata['subType']}, coinTxndata, True)

    cashBillTransactionState = formatcashBillTransaction(cashBillTransactionState['initialTubeStatus'], line_no)

def calculateBillRefundPrice():
    totalPrice = 0
    initTubeLevelArray = cashBillTransactionState['initialTubeStatus'].split(" ")
    afterRefundTubeLevelArray = cashBillTransactionState['afterRefundTubeStatus'].split(" ")
    index = 0

    while index < len(initTubeLevelArray) - 1:
        totalPrice += coinTubeLevelFormat[index] * 100 * (int(initTubeLevelArray[index]) - int(afterRefundTubeLevelArray[index]))
        index += 1

    return totalPrice  

# --------------------------- end check cash bill note ---------------------------

def ExportStateData(dir):
    # currDir = os.getcwd();
    # os.chdir(dir);
    # # os.chdir(dir);
    # path = ("./stateConfig.conf")
    with open(dir, 'w') as f:
        keys_values = cardTransactionState.items()
        cardTransactionStateString = str({str(key): str(value) for key, value in keys_values})
        f.write("cardTransactionState=" + cardTransactionStateString + "\n")

        coinTubeLevelFormatString = ','.join(str(e) for e in coinTubeLevelFormat)
        f.write("coinTubeLevelFormat=" + coinTubeLevelFormatString + "\n")

        keys_values = cashCoinTransactionState.items()
        cashCoinTransactionStateString = str({str(key): str(value) for key, value in keys_values})
        f.write("cashCoinTransactionState=" + cashCoinTransactionStateString + "\n") 

        billValueLevelFormatString = ','.join(str(e) for e in billValueLevelFormat)
        f.write("billValueLevelFormat=" + billValueLevelFormatString + "\n")       

        keys_values = cashBillTransactionState.items()
        cashBillTransactionStateString = str({str(key): str(value) for key, value in keys_values})
        f.write("cashBillTransactionState=" + cashBillTransactionStateString + "\n")         

        f.write("lastLineNum=" + str(lastLineNum) + "\n")  

def importMachineData(dir):
    global cardTransactionState
    global cashCoinTransactionState
    global cashBillTransactionState
    formatCardTransaction(0)
    formatCashCoinTransaction("", 0)
    cashBillTransactionState = formatcashBillTransaction("", 0)
    currDir = os.getcwd();
    os.chdir(dir);
    subDirs = glob.glob("./*")
    path = os.path.join(constants.BACKUP_LOG_DIR, dir, "stateConfig.conf")
    if not os.path.exists(path):
        open(path, 'x')
    print(dir)

    for subDir in subDirs:
        if (subDir[2:len(subDir)] == 'dev.conf'):
            ImportConfigData(subDir, dir)
        if (subDir[2:len(subDir)] == 'Logs.txt'):
            ImportLogData(subDir)
    ExportStateData(path)
    os.chdir(currDir);

def main():
    os.chdir(ProjectDirName);
    deviceDirs = glob.glob("./*")
    for dir in deviceDirs:
        if (len(dir) == 34):
            # if "1D7AB3425337433231202020FF0D0000" in dir:
                print(dir)
                importMachineData(dir);
            
    


if __name__ == "__main__":
    main()