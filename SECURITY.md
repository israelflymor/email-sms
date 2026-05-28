# Security Migration Guide

## Overview

This application has been migrated from API-key based authentication to industry-standard JWT (JSON Web Token) authentication with session management. This document outlines the security improvements and deployment considerations.

## Key Security Improvements

### 1. Authentication
- **From**: Simple API key lookup in configuration
- **To**: Secure JWT tokens with cryptographic signing
- **Benefits**:
  - Tokens are cryptographically signed and cannot be forged
  - Stateless authentication (no server-side API key lookup)
  - Tokens include expiration times
  - Support for refresh tokens with longer expiration
  - User-based authentication instead of API-key based

### 2. Password Security
- **Hashing**: bcrypt with configurable cost factor (default: 12 rounds)
- **Strength Validation**: 
  - Minimum 12 characters
  - Requires uppercase, lowercase, numbers, and special characters
  - Strength scoring system (0-100)
- **Change Management**:
  - All existing sessions revoked on password change
  - Cannot reuse current password
  - Audit logged for compliance

### 3. Brute-Force Protection
- **Account Lockout**: After 5 failed login attempts
- **Lockout Duration**: 15 minutes (configurable)
- **Rate Limiting**: IP-based login attempt rate limiting
  - 5 attempts per 5 minutes per IP
- **Automatic Unlock**: Accounts unlock after lockout period expires

### 4. Session Management
- **Session Tokens**: Each login creates a unique session in the database
- **Token JTI**: Unique JWT ID for session tracking
- **Session Revocation**: 
  - Sessions can be revoked on logout
  - Sessions expire automatically
  - All sessions can be revoked for emergency access revocation
- **Multi-Session Support**: Users can have multiple active sessions

### 5. Audit Logging
All authentication events are logged:
- Login attempts (success/failure)
- Logout events
- Token refresh
- Password changes
- Account lockouts

Each log entry includes:
- Event timestamp
- User ID and username
- IP address
- User agent
- Success/failure status
- Failure reason (if applicable)

### 6. Input Validation
- Username validation: alphanumeric + underscores only
- Password validation: strong password enforcement
- SQL injection prevention: parameterized queries
- XSS prevention: FastAPI automatic escaping

### 7. Token Security
- **Token Type**: HS256 HMAC
- **Access Token Expiration**: 15 minutes (short-lived)
- **Refresh Token Expiration**: 7 days
- **Token Claims**:
  - `sub`: Subject (user ID)
  - `username`: Username
  - `role`: User role
  - `jti`: JWT ID (unique identifier)
  - `type`: Token type (access/refresh)
  - `iat`: Issued at
  - `exp`: Expiration
- **Token Validation**: All claims verified on each request

## Configuration

### Required Environment Variables

```bash
# CRITICAL: Generate a strong random key (minimum 32 characters)
JWT_SECRET_KEY=your-very-secure-random-secret-key-32-chars-minimum

# Token expiration settings
JWT_EXPIRATION_MINUTES=15          # Access token lifetime
JWT_REFRESH_EXPIRATION_DAYS=7      # Refresh token lifetime
```

### Recommended Security Settings (for Production)

```bash
# HTTPS enforcement
REQUIRE_HTTPS=true

# CORS configuration
ALLOWED_ORIGINS=https://your-domain.com

# Brute-force protection
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=15

# Password requirements
PASSWORD_MIN_LENGTH=16
PASSWORD_REQUIRE_UPPERCASE=true
PASSWORD_REQUIRE_LOWERCASE=true
PASSWORD_REQUIRE_DIGITS=true
PASSWORD_REQUIRE_SPECIAL_CHARS=true
```

## Migration Steps

### 1. Generate JWT Secret

```bash
# Generate a cryptographically secure random key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 2. Database Migration

Run Alembic migrations to create new tables:

```bash
alembic upgrade head
```

New tables created:
- `admin_users`: User accounts with hashed passwords
- `user_sessions`: Active user sessions
- `auth_audit_logs`: Authentication event logs

### 3. Initialize Admin User

Create initial admin user (implementation required):

```python
from packages.auth.password import hash_password
from packages.db.models import AdminUser

admin = AdminUser(
    username="admin",
    email="admin@example.com",
    hashed_password=hash_password("InitialPassword123!"),
    role="admin",
    is_active=True,
)
db.add(admin)
db.commit()
```

### 4. Update Client Applications

Clients must be updated to use the new JWT authentication:

**Old API (DEPRECATED)**:
```bash
curl -H "Authorization: Bearer api_key_123" \
     https://api.example.com/admin/campaigns
```

**New API**:
```bash
# 1. Login to get tokens
curl -X POST https://api.example.com/auth/login \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "YourPassword123!"}'

# Response:
# {
#   "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "expires_in": 900,
#   "role": "admin",
#   "username": "admin"
# }

# 2. Use access token for requests
curl -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
     https://api.example.com/admin/campaigns

# 3. When token expires, refresh it
curl -X POST https://api.example.com/auth/refresh \
     -H "Content-Type: application/json" \
     -d '{"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."}'
```

## API Changes

### New Endpoints

#### POST /auth/login
User login with username/password.

**Request**:
```json
{
  "username": "admin",
  "password": "YourPassword123!"
}
```

**Response (200)**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 900,
  "role": "admin",
  "username": "admin"
}
```

#### POST /auth/refresh
Refresh access token using refresh token.

**Request**:
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response (200)**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 900
}
```

#### POST /auth/logout
Revoke current session.

**Headers**: `Authorization: Bearer <access_token>`

**Request**:
```json
{
  "all_sessions": false
}
```

**Response (200)**:
```json
{
  "message": "Logged out successfully"
}
```

#### POST /auth/change-password
Change user password.

**Headers**: `Authorization: Bearer <access_token>`

**Request**:
```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword456!",
  "confirm_password": "NewPassword456!"
}
```

**Response (200)**:
```json
{
  "message": "Password changed successfully"
}
```

## Security Best Practices

### For Operators

1. **Secret Management**:
   - Store JWT_SECRET_KEY in secure secret management system (AWS Secrets Manager, HashiCorp Vault, etc.)
   - Never commit secrets to version control
   - Rotate secrets regularly
   - Use different secrets for different environments

2. **HTTPS Enforcement**:
   - Set REQUIRE_HTTPS=true in production
   - Use valid TLS certificates
   - Enable HSTS (HTTP Strict-Transport-Security)

3. **Token Storage**:
   - Store tokens in memory or secure storage (NOT localStorage in browsers)
   - Use HTTPOnly cookies if possible
   - Use Secure flag for HTTPS-only transmission

4. **Session Management**:
   - Monitor auth_audit_logs table for suspicious activity
   - Implement log rotation
   - Alert on multiple failed login attempts from same IP

5. **Database Security**:
   - Ensure PostgreSQL is not accessible from internet
   - Use connection pooling
   - Enable query logging in production
   - Regular backups and testing

6. **Monitoring & Alerting**:
   - Monitor login attempt rates
   - Alert on account lockouts
   - Track token refresh patterns
   - Monitor for unusual IP addresses

### For Users

1. **Password Management**:
   - Use strong, unique passwords (12+ characters)
   - Include uppercase, lowercase, numbers, special characters
   - Use password manager
   - Never share credentials

2. **Token Handling**:
   - Don't expose tokens in logs or error messages
   - Don't commit tokens to version control
   - Use token refresh before expiration
   - Immediately logout when done

3. **Device Security**:
   - Log out from untrusted devices
   - Enable "revoke all sessions" if device is compromised
   - Use VPN on public networks

## Deprecated

### API Key Authentication
The old API key authentication via `ADMIN_API_KEYS` is deprecated and will be removed in a future version.

**Migration Path**:
1. Create admin user with strong password
2. Update applications to use JWT authentication
3. Remove ADMIN_API_KEYS from configuration
4. Delete legacy API key references

## Troubleshooting

### "JWT_SECRET_KEY not configured"
Set the JWT_SECRET_KEY environment variable:
```bash
export JWT_SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
```

### "Invalid token"
- Verify token is not expired
- Check Authorization header format: `Bearer <token>`
- Ensure JWT_SECRET_KEY matches between services

### "Account locked"
- Wait for lockout duration (default: 15 minutes)
- Or contact administrator to manually unlock

### "Rate limit exceeded"
- Wait 5 minutes before retrying
- Or try from different IP address

## Additional Resources

- [JWT.io](https://jwt.io/) - JWT specification
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [NIST Password Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
