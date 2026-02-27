# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

We take the security of Exchange Gateway seriously. If you discover a security vulnerability, please follow these steps:

### 1. Do Not Disclose Publicly

Please **do not** create a public GitHub issue for security vulnerabilities.

### 2. Report Privately

Send an email to **f148002@gmail.com** with:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### 3. Response Timeline

- **Initial Response**: Within 48 hours
- **Status Update**: Within 7 days
- **Fix Timeline**: Depends on severity
  - Critical: 1-7 days
  - High: 7-30 days
  - Medium: 30-90 days
  - Low: Best effort

### 4. Disclosure Policy

- We will work with you to understand and fix the issue
- We will credit you in the security advisory (unless you prefer to remain anonymous)
- We will coordinate disclosure timing with you

## Security Best Practices

When deploying Exchange Gateway:

1. **Always use HTTPS** in production
2. **Set strong SECRET_KEY and EXCHANGE_ENCRYPTION_KEY**
3. **Use Docker Secrets** for sensitive values in production
4. **Enable IP whitelisting** for API keys when possible
5. **Regularly rotate** API keys and encryption keys
6. **Keep dependencies updated** via `pip install -U -r requirements.txt`
7. **Monitor audit logs** for suspicious activity
8. **Use rate limiting** to prevent abuse

## Known Security Considerations

- Exchange account passwords are encrypted with AES-256-GCM
- API keys are hashed with SHA-256 before storage
- JWT tokens expire after 7 days by default
- Webhook URLs are validated (private IPs blocked in production by default)

## Security Updates

Security updates will be released as patch versions and announced via:
- GitHub Security Advisories
- CHANGELOG.md
- Release notes
