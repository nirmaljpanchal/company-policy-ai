import argparse
import os
import sys
from uuid import uuid4

from sqlalchemy import select

from app.auth.security import hash_password
from app.config import get_settings
from app.db import SessionLocal
from app.models.user import User


def main():
    parser = argparse.ArgumentParser(description="Seed an admin user into the database")
    parser.add_argument(
        "--email",
        default=os.getenv("SEED_ADMIN_EMAIL"),
        help="Admin email (default: env SEED_ADMIN_EMAIL)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("SEED_ADMIN_PASSWORD"),
        help="Admin password (default: env SEED_ADMIN_PASSWORD)",
    )
    args = parser.parse_args()

    if not args.email or not args.password:
        parser.print_help()
        sys.exit(1)

    # Validate settings to ensure DB connection works
    try:
        get_settings()
    except Exception as e:
        print(f"Error loading settings: {e}")
        sys.exit(1)

    db = SessionLocal()
    try:
        # Check if user exists
        stmt = select(User).where(User.email == args.email)
        existing_user = db.scalar(stmt)

        if existing_user:
            # Update existing user
            existing_user.password_hash = hash_password(args.password)
            existing_user.role = "admin"
            existing_user.is_active = True
            db.add(existing_user)
            db.commit()
            db.refresh(existing_user)
            print(f"✓ Updated admin user: {existing_user.email} (id: {existing_user.id})")
        else:
            # Create new user
            user = User(
                id=uuid4(),
                email=args.email,
                password_hash=hash_password(args.password),
                role="admin",
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"✓ Created admin user: {user.email} (id: {user.id})")

    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
