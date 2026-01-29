import os
import json
import time
import threading
import requests
import gspread
from datetime import datetime
from flask import Flask
from google.oauth2.service_account import Credentials

# ================== FLASK ==================
app = Flask(__name__)

@app.route("/")
def home():
    return "Vote tracker is running", 200


# ================== CONFIG ==================
API_URL = "https://voting.net-solutions.vn/wechoice/v2/voting/vote-count"
PARAMS = {
    "awardId": "1139348144238723073",
    "save": 1,
    "sessionToken": "PUT_YOUR_SESSION_TOKEN_HERE"
}

SHEET_ID = "1magHA2dA4Z0j2qUJqsF4bHIWzrmJyGGNQ1MqQQx_GMQ"
FETCH_INTERVAL = 5  # seconds (>=30s cho an toàn quota)

CUONG_BACH_ID = 66
CONGB_ID = 58
PHUC_NGUYEN_ID = 61


# ================== GOOGLE SHEETS ==================
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
    r = requests.get(API_URL, params=PARAMS, timeout=15)
    r.raise_for_status()
    data = r.json()
    return {
        i["finalCandidateId"]: i["voteCount"]
        for i in data["data"]["data"][0]["countInfo"]
    }


def update_google_sheet():
    global prev_gap_cong, prev_gap_phuc

    votes = fetch_votes()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cb = votes.get(CUONG_BACH_ID, 0)
    cong = votes.get(CONGB_ID, 0)
    phuc = votes.get(PHUC_NGUYEN_ID, 0)

    cb_prev = prev_votes.get(CUONG_BACH_ID, cb)
    cong_prev = prev_votes.get(CONGB_ID, cong)
    phuc_prev = prev_votes.get(PHUC_NGUYEN_ID, phuc)

    # Growth
    cb_growth = cb - cb_prev
    cong_growth = cong - cong_prev
    phuc_growth = phuc - phuc_prev

    # Gap
    gap_cong = cb - cong
    gap_phuc = cb - phuc

    # Gap growth
    gap_cong_growth = 0 if prev_gap_cong is None else gap_cong - prev_gap_cong
    gap_phuc_growth = 0 if prev_gap_phuc is None else gap_phuc - prev_gap_phuc

    row = [
        now,
        cb, cb_growth,
        cong, cong_growth, gap_cong, gap_cong_growth,
        phuc, phuc_growth, gap_phuc, gap_phuc_growth
    ]

    sheet.append_row(row, value_input_option="RAW")

    # Update state
    prev_votes.update(votes)
    prev_gap_cong = gap_cong
    prev_gap_phuc = gap_phuc

    print(f"[{now}] Updated sheet | CB={cb} CongB={cong} Phuc={phuc}")


def vote_worker():
    while True:
        try:
            update_google_sheet()
        except Exception as e:
            print("Worker error:", e)
        time.sleep(FETCH_INTERVAL)


# ================== ENTRY ==================
if __name__ == "__main__":
    threading.Thread(target=vote_worker, daemon=True).start()

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )



