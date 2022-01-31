# log root directory 
ORIGINAL_LOG_DIR = "D:/2021-Workspace/0514_vending_portal_Australia/vgc2"

# backup log directory
BACKUP_LOG_DIR = "D:/2021-Workspace/0514_vending_portal_Australia/vgc2_backup"


# finding value patterns.
ITEM_PRICE_PATTERN = "Price: (.+?)\.$"

# ------------------------------------ card constants ----------------------------------------------
# finding value pattern
CARD_PRE_AUTH_AMOUNT_PATTERN = "TXN AUTH OK for amount:(.+?)\."
CARD_SELECTED_ITEM_PATTERN = "MDBS: CD <= VEND REQUEST Item:(.+?)\, Price"
CARD_GET1_VALUE_PATTERN = "CMV300: TXN_GET1: (.+?)$"

# finding line patterns.
CARD_TANSACTION_START = "CMV300: TXN AUTH"
CARD_PRE_AUTH_OK = "TXN AUTH OK for amount:"
CARD_PRE_AUTH_FAIL = [
    "CMV300: TXN AUTH Declined", 
    "CMV300: TXN AUTH Resp Timeout",  
    "CMV300: TXN AUTH Failed. Status",
    "CMV300: TXN AUTH timeout" 
]
CARD_SELECT_ITEM = "MDBS: CD <= VEND REQUEST Item:"
CARD_NO_ITEM_SELECTED = "CMV300: No item selected."

CARD_VEND_CANCEL = "MDBS: CD <= VEND CANCEL."
CARD_VEND_FAIL_CANCEL = "CMV300: Vend FAIL. Send: CANCEL."
CARD_VEND_FAIL_VOID = "CMV300: Vend FAIL. Send: VOID."
CARD_TXN_AUTH_CANCEL = "CMV300: TXN AUTH Cancelled."

CARD_VEND_SUCCESS = "MDBS: CD <= VEND SUCCESS."
CARD_SESSION_COM = "MDBS: CD <= SESSION COMPLETE."
CARD_GET1 = "CMV300: TXN_GET1:"

# card transaction fail reason
CARD_FAIL_REASON = {
	"PRE_AUTH_FAIL": "PRE_AUTH_FAIL",
	"NO_ITEM_SELECTED": "NO_ITEM_SELECTED",
	"VEND_FAIL_SEND_CANCEL": "VEND_FAIL_SEND_CANCEL",
	"VEND_FAIL_SEND_VOID": "VEND_FAIL_SEND_VOID",
	"TXN_AUTH_CANCEL": "TXN_AUTH_CANCEL",
}

# ----------------------------------------- end card constants -------------------------------------

# ---------------------------------------------- cash constants ---------------------------------------
# finding pattern
CASH_CONFIG_PATTERN = "CoinValues\(\$\): (.+?)\.$"
CASH_COIN_TUBE_LEVEL_PATTERN = "TubeStatus: (.+?)\.$"
CASH_COIN_ROUTING_PRICE = "Routing: TUBES, Coin: (.+?), NumOfCoins"
CASH_COIN_CASHBOX_PRICE = "Routing: CASH BOX, Coin: (.+?), NumOfCoins"
CASH_COIN_ROUTING_LEVEL = "NumOfCoins: (.+?)\.$"
CASH_SELECTED_ITEM_PATTERN = "MDBS: OTHER <= VEND REQUEST Item: (.+?), Price"

CASH_COIN_CONFIG = "MDBS: COINCH: CONFIG:"
CASH_COIN_TUBE_LEVEL = "MDBS: COINCH: TubeFull:"
CASH_COIN_ROUTING_TUBES = "MDBS: COINCH: Routing:"
CASH_COIN_ROUTING_CASH_BOX = "MDBS: COINCH: Routing: CASH BOX"
CASH_SELECT_ITEM = "MDBS: OTHER <= VEND REQUEST Item:"
CASH_SESSION_COMPLETE = "MDBS: OTHER <= SESSION COMPLETE."
CASH_COIN_PAY_OUT = "MDBS: COINCH: Payout Status Total:"
CASH_COIN_ESCROW_REQUEST = "MDBS: COINCH: Escrow Request."

CASH_COIN_FAIL_REASON = {
	"TOTAL_REFUNDED": "TOTAL_REFUNDED",
	"NO_ITEM_SELECTED": "NO_ITEM_SELECTED"
}
# ---------------------------------------------- end cash constants ---------------------------------------

# ---------------------------------------------- cash bill constants ---------------------------------------
CASH_BILL_ESCROWED = "MDBS: BILLV: Escrowed: "

# ---------------------------------------------- end cash bill constants ---------------------------------------
