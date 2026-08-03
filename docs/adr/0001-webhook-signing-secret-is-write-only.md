# Webhook signing secret is write-only

Webhook signing secrets are encrypted at rest and may be supplied only when a subscription is created or deliberately rotated. The API, audit trail, and UI must never expose either the plaintext or ciphertext, because returning ciphertext enables accidental re-encryption and weakens the secret boundary. Every test and asynchronous delivery computes its HMAC from the decrypted original secret; ciphertext signing has no compatibility path.
