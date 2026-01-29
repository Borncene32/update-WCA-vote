import time
import requests
import gspread
import os
import json
from datetime import datetime
from google.oauth2.service_account import Credentials


from flask import Flask
import threading
import time

app = Flask(__name__)

def vote_worker():
    while True:
        update_google_sheet()
        time.sleep(30)

@app.route("/")
def home():
    return "OK", 200

if __name__ == "__main__":
    t = threading.Thread(target=vote_worker, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=10000)
# ================== CONFIG ==================
API_URL = "https://voting.net-solutions.vn/wechoice/v2/voting/vote-count"
PARAMS = {
    "awardId": "1139348144238723073",
    "save": 1,
    "sessionToken": "PUT_YOUR_SESSION_TOKEN_HERE"
}

CREDS_FILE = "credentials.json"
SHEET_ID = "1magHA2dA4Z0j2qUJqsF4bHIWzrmJyGGNQ1MqQQx_GMQ"
FETCH_INTERVAL = 10  # seconds

CUONG_BACH_ID = 66
CONGB_ID = 58
PHUC_NGUYEN_ID = 61

# ================== GOOGLE SHEETS ==================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])

creds = Credentials.from_service_account_info(
    creds_dict,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)

gc = gspread.authorize(creds)
sheet = gc.open_by_key(SHEET_ID).sheet1

# ================== STATE ==================
prev_votes = {}
prev_gap_cong = None
prev_gap_phuc = None

# ================== FUNCTIONS ==================
def fetch_votes():
    r = requests.get(API_URL, params=PARAMS, timeout=10)
    r.raise_for_status()
    data = r.json()
    return {
        i["finalCandidateId"]: i["voteCount"]
        for i in data["data"]["data"][0]["countInfo"]
    }

# ================== MAIN LOOP ==================
while True:
    votes = fetch_votes()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cb = votes[CUONG_BACH_ID]
    cong = votes[CONGB_ID]
    phuc = votes[PHUC_NGUYEN_ID]

    cb_prev = prev_votes.get(CUONG_BACH_ID, cb)
    cong_prev = prev_votes.get(CONGB_ID, cong)
    phuc_prev = prev_votes.get(PHUC_NGUYEN_ID, phuc)

    # --- Growth ---
    cb_growth = cb - cb_prev
    cong_growth = cong - cong_prev
    phuc_growth = phuc - phuc_prev

    # --- Gap ---
    gap_cong = cb - cong
    gap_phuc = cb - phuc

    # --- Gap Growth ---
    gap_cong_growth = 0 if prev_gap_cong is None else gap_cong - prev_gap_cong
    gap_phuc_growth = 0 if prev_gap_phuc is None else gap_phuc - prev_gap_phuc

    # --- Append row ---
    row = [
        now,               # A Time
        cb,                # B Cường Bạch
        cb_growth,         # C Growth
        cong,              # D CongB
        cong_growth,       # E Growth
        gap_cong,          # F Gap
        gap_cong_growth,   # G Gap Growth
        phuc,              # H Phúc Nguyên
        phuc_growth,       # I Growth
        gap_phuc,          # J Gap
        gap_phuc_growth    # K Gap Growth
    ]

    sheet.append_row(row, value_input_option="RAW")

    # --- update state ---
    prev_votes = votes.copy()
    prev_gap_cong = gap_cong
    prev_gap_phuc = gap_phuc

    time.sleep(FETCH_INTERVAL)


