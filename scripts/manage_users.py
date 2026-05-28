#!/usr/bin/env python
"""CLI tool for managing admin users."""
import sys
import getpass
import argparse
from datetime import datetime, timezone
import uuid

from sqlalchemy.orm import Session
from packages.db.session import SessionLocal
from packages.auth.models import AdminUser
from packages.auth.password import hash_password, is_password_strong

def create_admin_user(username: str, email: str, password: str = None, role: str = "admin") -> AdminUser:
    """Create a new admin user."""
    db = SessionLocal()
    try:
        # Check if user exists
        existing = db.query(AdminUser).filter(
            (AdminUser.username == username.lower()) | (AdminUser.email == email.lower())
        ).first()
        if existing:
            print(f"❌ Error: User '{username}' or email '{email}' already exists")
            return None
        
        # Get password if not provided
        if not password:
            while True:
                password = getpass.getpass(f"Enter password for {username}: ")
                confirm = getpass.getpass("Confirm password: ")
                
                if password != confirm:
                    print("❌ Passwords do not match")
                    continue
                
                is_strong, message = is_password_strong(password)
                if not is_strong:
                    print(f"❌ {message}")
                    continue
                
                break
        
        # Create user
        user = AdminUser(
            id=uuid.uuid4(),
            username=username.lower(),
            email=email.lower(),
            hashed_password=hash_password(password),
            role=role,
            is_active=True,
            is_locked=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        db.add(user)
        db.commit()
        print(f"✅ Admin user '{username}' created successfully")
        print(f"   - Role: {role}")
        print(f"   - Email: {email}")
        return user
    except Exception as e:
        print(f"❌ Error creating user: {e}")
        db.rollback()
        return None
    finally:
        db.close()

def list_admin_users() -> None:
    """List all admin users."""
    db = SessionLocal()
    try:
        users = db.query(AdminUser).all()
        if not users:
            print("No admin users found")
            return
        
        print("\n📋 Admin Users:")
        print("-" * 80)
        for user in users:
            status = "🟢 Active" if user.is_active else "🔴 Inactive"
            locked = " (LOCKED)" if user.is_locked else ""
            last_login = user.last_login_at.strftime("%Y-%m-%d %H:%M:%S UTC") if user.last_login_at else "Never"
            print(f"Username: {user.username:<20} Email: {user.email:<30}")
            print(f"  Role: {user.role:<10} Status: {status}{locked}")
            print(f"  Last Login: {last_login}")
            print(f"  Created: {user.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            print("-" * 80)
    finally:
        db.close()

def unlock_user(username: str) -> None:
    """Unlock a locked user account."""
    db = SessionLocal()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == username.lower()).first()
        if not user:
            print(f"❌ User '{username}' not found")
            return
        
        if not user.is_locked:
            print(f"✓ User '{username}' is not locked")
            return
        
        user.is_locked = False
        user.locked_until = None
        user.failed_login_attempts = 0
        db.commit()
        print(f"✅ User '{username}' unlocked successfully")
    except Exception as e:
        print(f"❌ Error unlocking user: {e}")
        db.rollback()
    finally:
        db.close()

def reset_password(username: str) -> None:
    """Reset user password."""
    db = SessionLocal()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == username.lower()).first()
        if not user:
            print(f"❌ User '{username}' not found")
            return
        
        while True:
            password = getpass.getpass(f"Enter new password for {username}: ")
            confirm = getpass.getpass("Confirm password: ")
            
            if password != confirm:
                print("❌ Passwords do not match")
                continue
            
            is_strong, message = is_password_strong(password)
            if not is_strong:
                print(f"❌ {message}")
                continue
            
            break
        
        user.hashed_password = hash_password(password)
        user.password_changed_at = datetime.now(timezone.utc)
        db.commit()
        print(f"✅ Password reset for user '{username}'")
    except Exception as e:
        print(f"❌ Error resetting password: {e}")
        db.rollback()
    finally:
        db.close()

def deactivate_user(username: str) -> None:
    """Deactivate a user account."""
    db = SessionLocal()
    try:
        user = db.query(AdminUser).filter(AdminUser.username == username.lower()).first()
        if not user:
            print(f"❌ User '{username}' not found")
            return
        
        user.is_active = False
        db.commit()
        print(f"✅ User '{username}' deactivated")
    except Exception as e:
        print(f"❌ Error deactivating user: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """Main CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Admin user management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create new admin user")
    create_parser.add_argument("username", help="Username")
    create_parser.add_argument("email", help="Email address")
    create_parser.add_argument("--password", help="Password (will prompt if not provided)")
    create_parser.add_argument("--role", default="admin", choices=["admin", "operator", "reviewer", "viewer"], help="User role")
    
    # List command
    subparsers.add_parser("list", help="List all admin users")
    
    # Unlock command
    unlock_parser = subparsers.add_parser("unlock", help="Unlock locked account")
    unlock_parser.add_argument("username", help="Username to unlock")
    
    # Reset password command
    reset_parser = subparsers.add_parser("reset-password", help="Reset user password")
    reset_parser.add_argument("username", help="Username to reset password")
    
    # Deactivate command
    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate user account")
    deactivate_parser.add_argument("username", help="Username to deactivate")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "create":
        create_admin_user(args.username, args.email, args.password, args.role)
    elif args.command == "list":
        list_admin_users()
    elif args.command == "unlock":
        unlock_user(args.username)
    elif args.command == "reset-password":
        reset_password(args.username)
    elif args.command == "deactivate":
        deactivate_user(args.username)

if __name__ == "__main__":
    main()
