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
from app.schemas.exchange import EmailListRequest

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
            return

        print(f"Using account: {account.email} (ID: {account.id})")
        
        service = EmailService()
        
        # 1. Get an email to test with
        print("\n--- step 1: List Emails to find a target ---")
        request = EmailListRequest(account_id=account.id, limit=5)
        response = await service.list_emails(request)
        
        if not response['success'] or not response['items']:
            print("Failed to list emails or no emails found.")
            return

        target_email = response['items'][0]
        original_status = target_email.is_read
        print(f"Target Email: {target_email.subject}")
        print(f"Original Status: {'READ' if original_status else 'UNREAD'}")
        
        # 2. Toggle Status
        new_status = not original_status
        print(f"\n--- step 2: Mark as {'READ' if new_status else 'UNREAD'} ---")
        
        mark_response = await service.mark_as_read(
            account_id=account.id,
            email_id=target_email.id,
            is_read=new_status
        )
        print(f"Mark Response: {mark_response}")
        
        # 3. Verify
        print("\n--- step 3: Verify Status ---")
        detail_response = await service.get_email(account_id=account.id, email_id=target_email.id)
        if detail_response['success']:
            current_status = detail_response['data']['is_read']
            print(f"Current Status: {'READ' if current_status else 'UNREAD'}")
            
            if current_status == new_status:
                print("SUCCESS: Status updated correctly.")
            else:
                print("FAILURE: Status did not update.")
        else:
            print(f"Failed to get email detail: {detail_response.get('message')}")
            
        # 4. Restore Status (Optional, but good practice)
        print(f"\n--- step 4: Restore Original Status ({'READ' if original_status else 'UNREAD'}) ---")
        await service.mark_as_read(
            account_id=account.id,
            email_id=target_email.id,
            is_read=original_status
        )
        print("Restored.")

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(main())
