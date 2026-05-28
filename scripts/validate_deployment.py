"""Deployment checklist and validation script."""
import sys
import os
import logging
from pathlib import Path
from sqlalchemy.orm import Session
from packages.config.settings import settings
from packages.db.session import SessionLocal
from packages.db.models import AdminUser

logger = logging.getLogger(__name__)

class DeploymentValidator:
    """Validate deployment readiness."""
    
    def __init__(self):
        self.checks = []
        self.warnings = []
        self.errors = []
    
    def check_environment_variables(self) -> bool:
        """Check required environment variables."""
        print("\n🔍 Checking environment variables...")
        
        required = {
            "JWT_SECRET_KEY": "JWT secret key",
            "DATABASE_URL": "Database connection string",
            "REDIS_URL": "Redis connection string",
        }
        
        all_set = True
        for var, description in required.items():
            if os.getenv(var):
                print(f"  ✅ {var}: Set")
                self.checks.append(f"{var} configured")
            else:
                print(f"  ❌ {var}: NOT SET - {description}")
                self.errors.append(f"Missing {var}")
                all_set = False
        
        # Warnings for development settings
        if not settings.require_https:
            print(f"  ⚠️  REQUIRE_HTTPS=false (development mode)")
            self.warnings.append("HTTPS not enforced - only for development")
        
        return all_set
    
    def check_database_connection(self) -> bool:
        """Check database connection."""
        print("\n🔍 Checking database connection...")
        try:
            db = SessionLocal()
            db.execute("SELECT 1")
            db.close()
            print("  ✅ Database connection: OK")
            self.checks.append("Database accessible")
            return True
        except Exception as e:
            print(f"  ❌ Database connection failed: {e}")
            self.errors.append(f"Database error: {e}")
            return False
    
    def check_admin_users(self) -> bool:
        """Check if admin users exist."""
        print("\n🔍 Checking admin users...")
        try:
            db = SessionLocal()
            admin_count = db.query(AdminUser).filter(AdminUser.role == "admin").count()
            total_users = db.query(AdminUser).count()
            db.close()
            
            if admin_count > 0:
                print(f"  ✅ Found {admin_count} admin user(s) ({total_users} total)")
                self.checks.append(f"Admin users configured ({admin_count} admins, {total_users} total)")
                return True
            else:
                print(f"  ⚠️  No admin users found")
                self.warnings.append("No admin users configured - use: python scripts/manage_users.py create <username> <email>")
                return False
        except Exception as e:
            print(f"  ❌ Error checking users: {e}")
            self.errors.append(f"Admin check error: {e}")
            return False
    
    def check_migrations(self) -> bool:
        """Check if migrations are up to date."""
        print("\n🔍 Checking migrations...")
        migrations_dir = Path("migrations/versions")
        
        if migrations_dir.exists():
            migration_count = len(list(migrations_dir.glob("*.py")))
            print(f"  ✅ Found {migration_count} migration(s)")
            self.checks.append(f"Migrations present ({migration_count} files)")
            return True
        else:
            print(f"  ⚠️  Migrations directory not found")
            self.warnings.append("Run 'alembic upgrade head' to apply migrations")
            return False
    
    def check_jwt_secret_strength(self) -> bool:
        """Check JWT secret key strength."""
        print("\n🔍 Checking JWT secret strength...")
        secret = os.getenv("JWT_SECRET_KEY", "")
        
        if len(secret) < 32:
            print(f"  ❌ JWT_SECRET_KEY too short ({len(secret)}/32 characters minimum)")
            self.errors.append("JWT_SECRET_KEY insufficient length")
            return False
        elif len(secret) < 64:
            print(f"  ⚠️  JWT_SECRET_KEY could be stronger ({len(secret)}/64 recommended)")
            self.warnings.append("Consider using longer JWT_SECRET_KEY")
            return True
        else:
            print(f"  ✅ JWT_SECRET_KEY strength: OK ({len(secret)} characters)")
            self.checks.append("JWT secret strong")
            return True
    
    def check_cors_configuration(self) -> bool:
        """Check CORS configuration."""
        print("\n🔍 Checking CORS configuration...")
        
        if settings.allowed_origins:
            print(f"  ✅ CORS enabled for: {', '.join(settings.allowed_origins)}")
            self.checks.append("CORS configured")
            return True
        else:
            print(f"  ⚠️  CORS not configured")
            self.warnings.append("Configure ALLOWED_ORIGINS for production")
            return False
    
    def validate_all(self) -> bool:
        """Run all validation checks."""
        print("\n" + "="*60)
        print("🚀 DEPLOYMENT READINESS VALIDATION")
        print("="*60)
        
        self.check_environment_variables()
        self.check_jwt_secret_strength()
        self.check_database_connection()
        self.check_admin_users()
        self.check_migrations()
        self.check_cors_configuration()
        
        # Summary
        print("\n" + "="*60)
        print("📊 VALIDATION SUMMARY")
        print("="*60)
        
        print(f"\n✅ Checks Passed: {len(self.checks)}")
        for check in self.checks:
            print(f"   • {check}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings: {len(self.warnings)}")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if self.errors:
            print(f"\n❌ Errors: {len(self.errors)}")
            for error in self.errors:
                print(f"   • {error}")
            print("\n🔴 DEPLOYMENT NOT READY")
            return False
        
        if self.warnings:
            print("\n🟡 DEPLOYMENT READY (with warnings)")
        else:
            print("\n🟢 DEPLOYMENT READY")
        
        return True

if __name__ == "__main__":
    validator = DeploymentValidator()
    success = validator.validate_all()
    sys.exit(0 if success or not validator.errors else 1)
