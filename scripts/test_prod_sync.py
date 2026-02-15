import requests
import json
import urllib3
from typing import Optional

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_URL = "https://10.78.4.119:9998/api/v1"
API_KEY = "f763098035c107ea363506cab9d5ad0688e3009f05d000b45ae71b342b27b6e0"
ACCOUNT_ID = 9

HEADERS = {
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

def print_step(msg):
    print(f"\n{'='*50}\n{msg}\n{'='*50}")

def test_sync(sync_state: Optional[str] = None):
    url = f"{BASE_URL}/exchange/emails/sync"
    payload = {
        "account_id": ACCOUNT_ID,
        "folder": "INBOX",
        "limit": 10,  # Small limit for testing
        "sync_state": sync_state
    }
    
    print(f"Requesting Sync with sync_state: {sync_state}")
    try:
        response = requests.post(url, json=payload, headers=HEADERS, verify=False)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            # Success class returns code 200 for success
            if data.get('code') == 200: 
                inner_data = data.get('data', {})
                print(f"Success! Sync State: {inner_data.get('sync_state')}")
                items = inner_data.get('items', [])
                print(f"Items count: {len(items)}")
                for item in items[:3]:  # Print first 3 items
                    item_detail = item.get('item') or {}
                    print(f" - [{item['change_type']}] {item['id'][:20]}... {item_detail.get('subject', 'No Subject')}")
                return inner_data
            else:
                print(f"Failed: {data.get('msg')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
    return None

def test_mark_read(email_id: str, is_read: bool):
    status_str = "READ" if is_read else "UNREAD"
    print_step(f"Testing Mark as {status_str}")
    
    url = f"{BASE_URL}/exchange/emails/{email_id}/read"
    params = {
        "account_id": ACCOUNT_ID,
        "is_read": is_read
    }
    
    try:
        response = requests.put(url, params=params, headers=HEADERS, verify=False)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 200:
                print(f"Success: {data.get('msg')}")
                return True
            else:
                print(f"Failed: {data.get('msg')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
    return False

def check_email_status(email_id: str):
    print_step("Checking Email Status")
    url = f"{BASE_URL}/exchange/emails/{email_id}"
    params = {
        "account_id": ACCOUNT_ID
    }
    
    try:
        response = requests.get(url, params=params, headers=HEADERS, verify=False)
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 200:
                email = data['data']
                print(f"Email Status: Is Read = {email['is_read']}")
                return email['is_read']
            else:
                print(f"Failed to get email: {data.get('msg')}")
        else:
            print(f"Error getting email: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
    return None

def test_list_emails():
    print_step("Testing List Emails (Connectivity Check)")
    url = f"{BASE_URL}/exchange/emails/list"
    params = {
        "account_id": ACCOUNT_ID,
        "limit": 5,
        "folder": "INBOX"
    }
    try:
        response = requests.get(url, params=params, headers=HEADERS, verify=False)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 200:
                inner_data = data.get('data', {})
                total = inner_data.get('total')
                items = inner_data.get('items', [])
                print(f"Success! Total emails: {total}")
                return items
            else:
                print(f"Failed: {data.get('msg')}")
        else:
            print(f"Error: {response.text}")
    except Exception as e:
        print(f"Exception: {e}")
    return None

def main():
    print_step("Starting Production Test")
    
    # 0. Connectivity & Get IDs
    email_items = test_list_emails()
    if not email_items:
        print("List emails failed. Aborting.")
        return

    # 1. Sync Test
    print_step("1. Initial Sync Test")
    # Try with only_fields to see if it helps, though we want to test default too. use default first.
    sync_result = test_sync(None)
    
    if sync_result:
        print("Sync Service: WORKS")
    else:
        print("Sync Service: FAILED (Check server logs)")
    
    # 2. Mark Read/Unread Test
    # Use an email from list
    target_item = email_items[0]
    email_id = target_item['id']
    subject = target_item.get('subject', 'No Subject')
    print(f"\nTarget Email for Read Status Test:\nID: {email_id}\nSubject: {subject}")
    
    # Check current status
    original_status = check_email_status(email_id)
    if original_status is None:
        return

    # Toggle Status
    new_status = not original_status
    print_step(f"Attempting to change read status from {original_status} to {new_status}")
    
    if test_mark_read(email_id, new_status):
        # Verify
        current_status = check_email_status(email_id)
        if current_status == new_status:
            print("VERIFICATION SUCCESS: Status changed correctly.")
            # Restore
            print_step("Restoring Original Status")
            test_mark_read(email_id, original_status)
        else:
            print(f"VERIFICATION FAILED: Status is {current_status}, expected {new_status}.")
    else:
        print("Mark as read/unread call failed.")


if __name__ == "__main__":
    main()
