
import requests
import json
import logging
import sys

# Local server URL
API_BASE_URL = "http://127.0.0.1:8000/api/v1/exchange/emails"

# Credentials from User
API_KEY = "665a0eca0796aa573dc91590f07e2a2aa1e82f777e070f07b69383435c45d860"
ACCOUNT_ID = 5

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_reproduction():
    headers = {
        "Content-Type": "application/json",
        "X-Api-Key": API_KEY
    }
    
    # 1. Initial Sync (getting sync_state)
    logger.info("Step 1: Initial sync to get state...")
    try:
        resp = requests.post(
            f"{API_BASE_URL}/sync",
            headers=headers,
            json={
                "account_id": ACCOUNT_ID,
                "folder": "INBOX",
                "limit": 5,
                "sync_state": None
            }
        )
        resp.raise_for_status()
        data = resp.json().get("data", {})
        sync_state = data.get("sync_state")
        if sync_state:
            with open("bad_sync_state.txt", "w") as f:
                f.write(sync_state)
            logger.info(f"Got sync_state: {sync_state[:50]}... (saved to bad_sync_state.txt)")
    except Exception as e:
        logger.error(f"Initial sync failed: {e}")
        if 'resp' in locals(): logger.error(resp.text)
        return

    if not sync_state:
        logger.error("No sync_state returned!")
        return

    # 2. Subsequent Sync (sending back state)
    logger.info("Step 2: Sending back sync_state...")
    try:
        resp = requests.post(
            f"{API_BASE_URL}/sync",
            headers=headers,
            json={
                "account_id": ACCOUNT_ID,
                "folder": "INBOX",
                "limit": 5,
                "sync_state": sync_state
            }
        )
        
        logger.info(f"Response Status: {resp.status_code}")
        logger.info(f"Response Body: {resp.text}")
        
    except Exception as e:
        logger.error(f"Subsequent sync failed: {e}")

if __name__ == "__main__":
    run_reproduction()
