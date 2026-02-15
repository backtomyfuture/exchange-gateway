
import requests
import json
import logging
import time
import sys
import threading

# Local server URL
API_BASE_URL = "http://127.0.0.1:8000/api/v1/exchange/emails"

# Credentials
API_KEY = "665a0eca0796aa573dc91590f07e2a2aa1e82f777e070f07b69383435c45d860"
ACCOUNT_ID = 5 # yy-zhang1@tianjin-air.com (from list_accounts.py)
SELF_EMAIL = "yy-zhang1@tianjin-air.com"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

HEADERS = {
    "Content-Type": "application/json",
    "X-Api-Key": API_KEY
}

def verify_sync():
    sync_state = None
    created_item_id = None
    
    # 1. Initial Sync (Get Baseline State)
    logger.info("\n=== Step 1: Initial Sync (Baseline) ===")
    try:
        resp = requests.post(f"{API_BASE_URL}/sync", headers=HEADERS, json={
            "account_id": ACCOUNT_ID, "folder": "INBOX", "limit": 5, "sync_state": None
        })
        resp.raise_for_status()
        data = resp.json().get("data", {})
        sync_state = data.get("sync_state")
        logger.info(f"Initial sync successful. State prefix: {sync_state[:30]}...")
    except Exception as e:
        logger.error(f"Initial sync failed: {e}")
        return

    # 2. Send Email to Self
    logger.info("\n=== Step 2: Send Email to Self ===")
    subject = f"Auto Test Sync {time.time()}"
    try:
        resp = requests.post(f"{API_BASE_URL}/send", headers=HEADERS, json={
            "account_id": ACCOUNT_ID,
            "to": [SELF_EMAIL],
            "subject": subject,
            "body": "This is a test email for sync verification.",
            "body_type": "text"
        })
        resp.raise_for_status()
        logger.info("Email sent successfully.")
    except Exception as e:
        logger.error(f"Send failed: {e}")
        return

    # Wait for delivery
    logger.info("Waiting 10 seconds for email delivery...")
    time.sleep(10)

    # 3. Sync Check 1 (Expect 'create')
    logger.info("\n=== Step 3: Sync Check (Expect Create) ===")
    try:
        resp = requests.post(f"{API_BASE_URL}/sync", headers=HEADERS, json={
            "account_id": ACCOUNT_ID, "folder": "INBOX", "limit": 10, "sync_state": sync_state
        })
        resp.raise_for_status()
        data = resp.json().get("data", {})
        new_sync_state = data.get("sync_state")
        items = data.get("items", [])
        
        logger.info(f"Sync returned {len(items)} items.")
        
        # Find our email
        for item in items:
            change_type = item.get("change_type")
            details = item.get("item")
            item_id = item.get("id")
            
            # Note: create/update items have 'item' dict, others might not
            obj_subject = details.get("subject") if details else "N/A"
            
            logger.info(f" - [{change_type}] ID: {item_id}, Subject: {obj_subject}")
            
            if change_type == 'create' and obj_subject and subject in obj_subject:
                created_item_id = item_id
                logger.info(f"✅ Found created email! ID: {created_item_id}")
        
        if not created_item_id:
            logger.warning("❌ Did not find the new email in sync results. Maybe delay too short?")
            # Proceeding anyway usually fails next steps but we continue logic
        else:
             # Update state only if we advanced
             sync_state = new_sync_state
             
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return

    if not created_item_id:
        logger.error("Stopping test because email was not found.")
        return

    # 4. Mark as Read
    logger.info("\n=== Step 4: Mark as Read ===")
    try:
        # Note: email_id needs to be path encoded if it has slashes, but requests handles it
        # FastAPI route is /{email_id:path}/read
        # We need to ensure requests doesn't double encode or fail on slashes
        url = f"{API_BASE_URL}/{created_item_id}/read"
        # query param is_read=true
        resp = requests.put(url, headers=HEADERS, params={"account_id": ACCOUNT_ID, "is_read": True})
        resp.raise_for_status()
        logger.info("Mark as read successful.")
    except Exception as e:
        logger.error(f"Mark read failed: {e}")
        return

    logger.info("Waiting 5 seconds...")
    time.sleep(5)

    # 5. Sync Check 2 (Expect 'read_flag_change' or 'update')
    logger.info("\n=== Step 5: Sync Check (Expect Read Change) ===")
    try:
        resp = requests.post(f"{API_BASE_URL}/sync", headers=HEADERS, json={
            "account_id": ACCOUNT_ID, "folder": "INBOX", "limit": 10, "sync_state": sync_state
        })
        resp.raise_for_status()
        data = resp.json().get("data", {})
        new_sync_state = data.get("sync_state")
        items = data.get("items", [])
        
        logger.info(f"Sync returned {len(items)} items.")
        found_update = False
        for item in items:
            change_type = item.get("change_type")
            item_id = item.get("id")
            logger.info(f" - [{change_type}] ID: {item_id}")
            
            if item_id == created_item_id:
                found_update = True
                logger.info(f"✅ Found update for our item: {change_type}")
        
        if found_update:
            sync_state = new_sync_state
        else:
            logger.warning("❌ No update event found for this item.")
            
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return

    # 6. Delete Email
    logger.info("\n=== Step 6: Delete Email ===")
    try:
        url = f"{API_BASE_URL}/{created_item_id}"
        resp = requests.delete(url, headers=HEADERS, params={"account_id": ACCOUNT_ID})
        resp.raise_for_status()
        logger.info("Delete successful.")
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return

    logger.info("Waiting 5 seconds...")
    time.sleep(5)

    # 7. Sync Check 3 (Expect 'delete')
    logger.info("\n=== Step 7: Sync Check (Expect Delete) ===")
    try:
        resp = requests.post(f"{API_BASE_URL}/sync", headers=HEADERS, json={
            "account_id": ACCOUNT_ID, "folder": "INBOX", "limit": 10, "sync_state": sync_state
        })
        resp.raise_for_status()
        data = resp.json().get("data", {})
        items = data.get("items", [])
        
        logger.info(f"Sync returned {len(items)} items.")
        found_delete = False
        for item in items:
            change_type = item.get("change_type")
            item_id = item.get("id")
            logger.info(f" - [{change_type}] ID: {item_id}")
            
            if item_id == created_item_id:
                 # Depending on implementation, delete might just have ID
                found_delete = True
                logger.info(f"✅ Found delete event for our item: {change_type}")
        
        if not found_delete:
             logger.warning("❌ No delete event found.")
        else:
             logger.info("Test Lifecycle Completed Successfully!")

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return

if __name__ == "__main__":
    verify_sync()
