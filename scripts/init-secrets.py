#!/usr/bin/env python3
# =============================================================================
# Exchange Gateway - Initialize Docker Secrets (Windows / cross-platform)
# Run: python scripts/init-secrets.py
# =============================================================================
import base64
import os
from pathlib import Path

SECRETS_DIR = Path(__file__).resolve().parent.parent / "secrets"
SECRETS_DIR.mkdir(parents=True, exist_ok=True)


def generate_if_missing(filename: str, generator, desc: str) -> None:
    path = SECRETS_DIR / filename
    if path.is_file() and path.stat().st_size > 0:
        print(f"  [skip] {desc} already exists: {filename}")
    else:
        content = generator()
        path.write_text(content)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass  # Windows may not support chmod
        print(f"  [new]  {desc} generated: {filename}")


def main() -> None:
    print(f"Initializing secrets in {SECRETS_DIR} ...")
    print()

    generate_if_missing(
        "secret_key",
        lambda: os.urandom(32).hex(),
        "JWT Secret Key",
    )
    generate_if_missing(
        "exchange_encryption_key",
        lambda: base64.b64encode(os.urandom(32)).decode(),
        "Exchange Encryption Key",
    )
    generate_if_missing(
        "db_password",
        lambda: base64.b64encode(os.urandom(24)).decode(),
        "Database Password",
    )

    print()
    print("Done. Secrets directory:", SECRETS_DIR)
    print()
    print("Next steps:")
    print("  1. cp .env.example .env")
    print("  2. Edit .env — set EXCHANGE_SERVER, EXCHANGE_DOMAIN, EXCHANGE_EMAIL_SUFFIX")
    print("     (NO passwords or keys needed in .env — they are in secrets/)")
    print("  3. docker compose --profile local-db --profile local-redis up -d")


if __name__ == "__main__":
    main()
