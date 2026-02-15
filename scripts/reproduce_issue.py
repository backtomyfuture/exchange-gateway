
import requests
import json
import sys
import urllib.parse

API_BASE_URL = "http://127.0.0.1:8000/api/v1/exchange/emails"
# Using the key and account ID from context
API_KEY = "f763098035c107ea363506cab9d5ad0688e3009f05d000b45ae71b342b27b6e0"
ACCOUNT_ID = 8

headers = {
    "X-Api-Key": API_KEY,
    "Content-Type": "application/json"
}

def list_emails():
    print("Listing emails to find one with attachments...")
    try:
        resp = requests.get(f"{API_BASE_URL}/list", params={"account_id": ACCOUNT_ID, "limit": 20}, headers=headers)
        if resp.status_code != 200:
            print(f"Failed to list emails: {resp.status_code} {resp.text}")
            return []
        return resp.json().get("data", {}).get("items", [])
    except Exception as e:
        print(f"Error listing emails: {e}")
        return []

def get_email_details(email_id):
    # Quote the email ID to handle special characters safely
    quoted_id = urllib.parse.quote(email_id, safe='')
    print(f"Getting details for email {email_id[:20]}... (quoted: {quoted_id[:20]}...)")
    
    url = f"{API_BASE_URL}/{quoted_id}"
    try:
        resp = requests.get(url, params={"account_id": ACCOUNT_ID}, headers=headers)
        if resp.status_code != 200:
            print(f"Failed to get email details: {resp.status_code} {resp.text}")
            return None
        return resp.json().get("data")
    except Exception as e:
        print(f"Error getting details: {e}")
        return None

def main():
    emails = list_emails()
    target_email = None
    
    # Try to find one with 'has_attachments' = True
    for email in emails:
        if email.get('has_attachments'):
            target_email = email
            print(f"Found email with attachments: {email.get('subject')} (ID: {email.get('id')[:20]}...)")
            break
            
    if not target_email:
        print("No emails marked with 'has_attachments' found in the first 20 items.")
        if emails:
             print("Trying the first email anyway...")
             target_email = emails[0]
        else:
             print("No emails found at all.")
             sys.exit(0)

    details = get_email_details(target_email['id'])
    
    if details:
        attachments = details.get('attachments', [])
        print(f"\n--- Attachment Analysis for Email: {details.get('subject')} ---")
        print(f"Total Attachments: {len(attachments)}")
        
        for i, att in enumerate(attachments):
            print(f"\nAttachment {i+1}:")
            print(f"  Name: {att.get('name')}")
            print(f"  Type: {att.get('content_type')}")
            print(f"  Size: {att.get('size')}")
            
            # Check for content
            if 'content' in att:
                content = att['content']
                if content:
                    print(f"  Content Field: PRESENT, Length: {len(content)}")
                else:
                    print(f"  Content Field: PRESENT but EMPTY/NONE")
            else:
                print(f"  Content Field: MISSING")
                
            # Check for inline flags
            if 'is_inline' in att:
                 print(f"  Is Inline: {att['is_inline']}")
            else:
                 print(f"  Is Inline: MISSING")
                 
            if 'content_id' in att:
                 print(f"  Content ID: {att['content_id']}")
            else:
                 print(f"  Content ID: MISSING")

    else:
        print("Could not retrieve email details.")

if __name__ == "__main__":
    main()
