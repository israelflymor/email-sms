# Authentication & Security Migration - Deployment Checklist

## ✅ Phase 1: Code Implementation (COMPLETED)

- [x] JWT token generation and validation
- [x] Secure password hashing (bcrypt)
- [x] Session management database models
- [x] Rate limiting and brute-force protection
- [x] Audit logging system
- [x] Authentication endpoints (/login, /refresh, /logout, /change-password)
- [x] Role-based access control (RBAC)
- [x] Security headers and CORS middleware
- [x] Input validation and sanitization
- [x] Admin route JWT migration
- [x] Database migration for auth tables
- [x] User management CLI tool
- [x] Deployment validation script

## ⏳ Phase 2: Pre-Deployment (IN PROGRESS)

### Environment Setup
- [ ] Generate JWT_SECRET_KEY
  ```bash
  python -c "import secrets; print(secrets.token_urlsafe(32))"
  ```
- [ ] Set JWT_SECRET_KEY in environment or `.env`
- [ ] Verify DATABASE_URL configuration
- [ ] Verify REDIS_URL configuration
- [ ] Update ALLOWED_ORIGINS for CORS

### Database Preparation
- [ ] Run database migrations
  ```bash
  alembic upgrade head
  ```
- [ ] Verify auth tables created (admin_users, user_sessions, auth_audit_logs)
- [ ] Create initial admin user
  ```bash
  python scripts/manage_users.py create admin admin@example.com
  ```

### Validation
- [ ] Run deployment validator
  ```bash
  python scripts/validate_deployment.py
  ```
- [ ] Review validation results
- [ ] Address any errors or warnings

## ⏳ Phase 3: Testing (READY FOR)

### Local Testing
- [ ] Start development server
  ```bash
  uvicorn apps.api.main:app --reload
  ```
- [ ] Test login endpoint
  ```bash
  curl -X POST http://localhost:8001/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "admin", "password": "YourPassword123!"}'
  ```
- [ ] Test protected endpoints with token
- [ ] Test token refresh
- [ ] Test rate limiting (5 failed logins)
- [ ] Test account lockout
- [ ] Test password change
- [ ] Test logout and session revocation

### Integration Testing
- [ ] Test admin endpoints with JWT
- [ ] Verify role-based access control
- [ ] Test audit logging
- [ ] Verify security headers
- [ ] Test CORS configuration

## ⏳ Phase 4: Production Deployment

### Pre-Deployment Checklist
- [ ] Set REQUIRE_HTTPS=true
- [ ] Configure trusted hosts
- [ ] Set up HTTPS/TLS certificates
- [ ] Configure reverse proxy (nginx/haproxy)
- [ ] Set up log aggregation
- [ ] Configure monitoring and alerting
- [ ] Set up database backups
- [ ] Configure Redis persistence

### Security Hardening
- [ ] Store JWT_SECRET_KEY in secrets manager (AWS Secrets Manager, Vault, etc.)
- [ ] Enable database encryption at rest
- [ ] Enable database encryption in transit
- [ ] Configure VPC/network security
- [ ] Set up WAF (Web Application Firewall) if applicable
- [ ] Enable request rate limiting at proxy level
- [ ] Configure DDoS protection

### Deployment Steps
- [ ] Build and test Docker image
- [ ] Push to container registry
- [ ] Deploy to staging environment
- [ ] Run full test suite on staging
- [ ] Verify all features work correctly
- [ ] Monitor staging for 24+ hours
- [ ] Deploy to production
- [ ] Monitor production closely for 24+ hours

### Post-Deployment
- [ ] Verify all services running
- [ ] Check application logs for errors
- [ ] Monitor CPU, memory, disk usage
- [ ] Monitor authentication metrics
- [ ] Test automated backup procedures
- [ ] Document runbook for incidents

## ⏳ Phase 5: Migration of Existing Users

### For existing systems using API keys:
- [ ] Create admin users for each API key holder
- [ ] Notify users of new JWT authentication
- [ ] Provide migration guide
- [ ] Set deprecation date for API keys (30-60 days)
- [ ] Monitor for deprecated API key usage
- [ ] Remove API key authentication code after deprecation period

## Configuration Reference

### Required Environment Variables
```bash
# JWT & Authentication
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_EXPIRATION_MINUTES=15
JWT_REFRESH_EXPIRATION_DAYS=7

# Database & Cache
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/db
REDIS_URL=redis://redis:6379/0

# Security
REQUIRE_HTTPS=true          # In production
ALLOWED_ORIGINS=https://domain.com
MAX_LOGIN_ATTEMPTS=5
LOGIN_LOCKOUT_MINUTES=15
```

## Troubleshooting

### Database Connection Errors
```bash
# Check database is accessible
psql $DATABASE_URL -c "SELECT 1;"

# Verify Alembic migrations
alembic current
alembic history
```

### JWT Token Errors
```bash
# Verify JWT_SECRET_KEY is set
echo $JWT_SECRET_KEY

# Check key length
python -c "print(len('$JWT_SECRET_KEY'))"
```

### Admin User Creation Failed
```bash
# List existing users
python scripts/manage_users.py list

# Reset password if needed
python scripts/manage_users.py reset-password admin
```

## Rollback Plan

If issues occur in production:

1. **Stop accepting new JWT tokens**: Set JWT_SECRET_KEY to invalid value temporarily
2. **Revert to previous version**: Deploy previous working commit
3. **Investigate logs**: Check auth_audit_logs for issues
4. **Fix and redeploy**: After root cause identified

## Support & Documentation

- [SECURITY.md](../SECURITY.md) - Complete security documentation
- [JWT Best Practices](https://tools.ietf.org/html/rfc7519)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
- [Alembic Migrations](https://alembic.sqlalchemy.org/)

## Success Criteria

✅ All deployment checklist items completed
✅ All validation checks passing
✅ All tests passing in production
✅ No authentication errors in logs
✅ Audit trail showing successful logins
✅ Security headers present in all responses
✅ Rate limiting functioning correctly
✅ Account lockout working as expected
✅ Token refresh working smoothly
✅ Session management working correctly
