import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import bcrypt
from datetime import datetime, timezone

async def create_demo_user():
    db = AsyncIOMotorClient('mongodb://localhost:27017')['accident_detection']
    
    async def ensure_user(email: str, name: str, role: str, user_id: str):
        existing = await db.users.find_one({'email': email})
        if existing:
            print(f"User {email} already exists.")
            return

        password = 'password123'.encode('utf-8')
        hashed = bcrypt.hashpw(password, bcrypt.gensalt())
        hashed_str = hashed.decode('utf-8')

        user_doc = {
            'id': user_id,
            'email': email,
            'name': name,
            'role': role,
            'password': hashed_str,
            'created_at': datetime.now(timezone.utc).isoformat()
        }

        await db.users.insert_one(user_doc)
        print(f"User {email} inserted successfully with role {role}.")

    # Admin demo user
    await ensure_user(
        email='admin@demo.com',
        name='Demo Admin',
        role='admin',
        user_id='demo-admin-id'
    )

    # Emergency services demo user
    await ensure_user(
        email='emergency@demo.com',
        name='Demo Emergency',
        role='emergency_services',
        user_id='demo-emergency-id'
    )

if __name__ == "__main__":
    asyncio.run(create_demo_user())
