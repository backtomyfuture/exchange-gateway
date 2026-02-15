import asyncio
import os
import sys
from dotenv import load_dotenv
from tortoise import Tortoise

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set DEV_MODE=true for local testing
os.environ["DEV_MODE"] = "true"

# Set Secrets Files
secrets_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".secrets"))
os.environ["EXCHANGE_ENCRYPTION_KEY_FILE"] = os.path.join(secrets_dir, "exchange_encryption_key")
os.environ["SECRET_KEY_FILE"] = os.path.join(secrets_dir, "secret_key")
os.environ["DB_PASSWORD_FILE"] = os.path.join(secrets_dir, "db_password")

from app.settings import settings
from app.models.exchange import ExchangeAccount
from app.services.exchange.email_service import EmailService
from app.schemas.exchange import EmailListRequest, EmailSearchRequest

async def main():
    # Load .env
    load_dotenv()
    
    # Init DB
    print("Initializing Database...")
    try:
        await Tortoise.init(config=settings.TORTOISE_ORM)
        print("Database Initialized.")
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        return

    try:
        # Get first account
        account = await ExchangeAccount.first()
        if not account:
            print("No ExchangeAccount found in database.")
            # List all accounts if any
            count = await ExchangeAccount.all().count()
            print(f"Total accounts found: {count}")
            return

        print(f"Using account: {account.email} (ID: {account.id})")
        
        service = EmailService()
        
        # Test List Emails
        print("\n--- Testing List Emails ---")
        request = EmailListRequest(account_id=account.id, limit=5)
        response = await service.list_emails(request)
        
        if response['success'] and response['items']:
            print(f"Success! Total emails: {response['total']}")
            first_email = response['items'][0]
            for item in response['items']:
                print(f" - [{item.received_time}] {item.subject} (From: {item.sender})")
            
            # Test Get Email Detail
            print("\n--- Testing Get Email Detail ---")
            print(f"Fetching details for email ID: {first_email.id}")
            detail_response = await service.get_email(account_id=account.id, email_id=first_email.id)
            if detail_response['success']:
                print("Success! Email details:")
                data = detail_response['data']
                print(f" - Subject: {data.get('subject')}")
                print(f" - Body Preview: {data.get('body')[:100] if data.get('body') else 'No body'}...")
                print(f" - Attachments: {len(data.get('attachments', []))}")
            else:
                print(f"Failed to get email detail: {detail_response.get('message')}")

            # Test Search Emails
            print("\n--- Testing Search Emails ---")
            search_query = first_email.subject
            print(f"Searching for subject: {search_query}")
            search_request = EmailSearchRequest(
                account_id=account.id, 
                query=search_query,
                limit=5
            )
            search_response = await service.search_emails(search_request)
            if search_response['success']:
                print(f"Success! Found {search_response['total']} matches.")
                for item in search_response['items']:
                    print(f" - [{item.received_time}] {item.subject}")
            else:
                print(f"Failed to search emails: {search_response.get('message')}")

        elif response['success']:
            print("Success but no emails found to test detail/search.")
        else:
            print(f"Failed to list emails: {response.get('message')}")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
