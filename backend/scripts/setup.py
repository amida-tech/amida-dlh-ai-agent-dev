#!/usr/bin/env python3
"""
Setup script for Amida AI Ticket Orchestrator backend
"""
import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from app.db.base import Base
from app.models import user, ticket, audit  # Import all models
from app.services.auth import get_password_hash


async def create_database():
    """Create database tables"""
    print("Creating database tables...")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("Database tables created successfully!")


async def create_admin_user():
    """Create initial admin user"""
    from app.db.session import AsyncSessionLocal
    from app.models import User, UserRole
    
    print("Creating admin user...")
    
    async with AsyncSessionLocal() as db:
        # Check if admin user already exists
        from sqlalchemy import select
        query = select(User).where(User.username == "admin")
        result = await db.execute(query)
        existing_user = result.scalars().first()
        
        if existing_user:
            print("Admin user already exists!")
            return
        
        # Create admin user
        admin_user = User(
            email="admin@amida.ai",
            username="admin",
            full_name="System Administrator",
            hashed_password=get_password_hash("admin123"),
            role=UserRole.ADMIN,
            is_active=True,
            is_verified=True
        )
        
        db.add(admin_user)
        await db.commit()
        
        print("Admin user created!")
        print("Username: admin")
        print("Password: admin123")
        print("Please change the password after first login!")


async def test_connections():
    """Test database and Redis connections"""
    print("Testing connections...")
    
    # Test database connection
    try:
        engine = create_async_engine(settings.DATABASE_URL)
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✓ Database connection successful")
        await engine.dispose()
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False
    
    # Test Redis connection
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        print("✓ Redis connection successful")
    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False
    
    return True


async def main():
    """Main setup function"""
    print("=" * 50)
    print("Amida AI Ticket Orchestrator - Backend Setup")
    print("=" * 50)
    
    # Test connections first
    if not await test_connections():
        print("\nSetup failed due to connection issues!")
        return
    
    # Create database tables
    await create_database()
    
    # Create admin user
    await create_admin_user()
    
    print("\n" + "=" * 50)
    print("Setup completed successfully!")
    print("=" * 50)
    print("\nNext steps:")
    print("1. Copy .env.example to .env and configure your settings")
    print("2. Start the development server: uvicorn main:app --reload")
    print("3. Start Celery worker: celery -A app.tasks.celery_app worker --loglevel=info")
    print("4. Access the API docs at: http://localhost:8000/docs")


if __name__ == "__main__":
    asyncio.run(main())