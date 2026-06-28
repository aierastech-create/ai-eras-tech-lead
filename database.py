import os
import logging
from datetime import datetime, timezone
import hashlib
from dotenv import load_dotenv
from pymongo import MongoClient
from bson import ObjectId

# Load environment variables
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")

if not MONGODB_URI:
    logging.error("MongoDB URI not found in environment variables.")
    client = None
    db = None
    users_collection = None
else:
    try:
        client = MongoClient(MONGODB_URI)
        # Use database name 'google_maps_scraper'
        db = client["google_maps_scraper"]
        users_collection = db["users"]
    except Exception as e:
        logging.error(f"Error connecting to MongoDB: {e}")
        client = None
        db = None
        users_collection = None

def hash_password(password):
    """Simple SHA256 hashing for passwords."""
    return hashlib.sha256(password.encode()).hexdigest()

def serialize_user(user_doc):
    """Convert MongoDB _id to string id for compatibility with the rest of the application."""
    if not user_doc:
        return None
    user_doc = dict(user_doc)
    user_doc['id'] = str(user_doc['_id'])
    return user_doc

def init_db():
    """
    Initializes the database. 
    Ensures the Super Admin exists.
    """
    if users_collection is None:
        return

    admin_email = os.getenv("ADMIN_EMAIL", "aierastech@gmail.com")
    admin_pass = os.getenv("ADMIN_PASSWORD", "Aierastech@987")
    hashed_pass = hash_password(admin_pass)

    # Check if admin exists
    try:
        user = users_collection.find_one({"email": admin_email})
        if not user:
            # Create admin
            users_collection.insert_one({
                "username": "Admin",
                "email": admin_email,
                "password": hashed_pass,
                "is_verified": True,
                "is_active": True,
                "is_admin": True,
                "phone": "",
                "otp": None,
                "last_login": None,
                "created_at": datetime.now(timezone.utc)
            })
            logging.info("Super Admin created in MongoDB.")
        else:
            # Update admin password just in case
            users_collection.update_one(
                {"email": admin_email},
                {"$set": {
                    "password": hashed_pass,
                    "is_admin": True,
                    "is_active": True
                }}
            )
            logging.info("Super Admin updated in MongoDB.")
    except Exception as e:
        logging.error(f"Error initializing MongoDB: {e}")

def register_user(username, email, phone, password, is_admin=False):
    """Registers a new user."""
    if users_collection is None:
        return False
    
    hashed = hash_password(password)
    try:
        # Check uniqueness of username and email
        if users_collection.find_one({"$or": [{"username": username}, {"email": email}]}):
            logging.warning(f"Registration failed: username '{username}' or email '{email}' already exists.")
            return False

        result = users_collection.insert_one({
            "username": username,
            "email": email,
            "phone": phone,
            "password": hashed,
            "is_verified": False,
            "is_active": False,
            "is_admin": is_admin,
            "otp": None,
            "last_login": None,
            "created_at": datetime.now(timezone.utc)
        })
        return result.acknowledged
    except Exception as e:
        logging.error(f"Registration error: {e}")
        return False

def get_user_by_email(email):
    if users_collection is None:
        return None
    try:
        user = users_collection.find_one({"email": email})
        return serialize_user(user)
    except Exception as e:
        logging.error(f"Error fetching user by email: {e}")
        return None

def get_user_by_username(username):
    if users_collection is None:
        return None
    try:
        user = users_collection.find_one({"username": username})
        return serialize_user(user)
    except Exception as e:
        logging.error(f"Error fetching user by username: {e}")
        return None

def authenticate_user(identifier, password):
    """Authenticates by email or username."""
    if users_collection is None:
        return None
    
    hashed = hash_password(password)
    try:
        user = users_collection.find_one({
            "$or": [{"email": identifier}, {"username": identifier}],
            "password": hashed
        })
        if user:
            now = datetime.now(timezone.utc).isoformat()
            users_collection.update_one({"_id": user["_id"]}, {"$set": {"last_login": now}})
            # Re-fetch user or just update in dictionary
            user["last_login"] = now
            return serialize_user(user)
    except Exception as e:
        logging.error(f"Authentication error: {e}")
        
    return None

def set_user_otp(email, otp):
    if users_collection is None:
        return
    try:
        users_collection.update_one({"email": email}, {"$set": {"otp": otp}})
    except Exception as e:
        logging.error(f"Error setting OTP: {e}")

def verify_user_otp(email, otp):
    if users_collection is None:
        return False
    try:
        user = users_collection.find_one({"email": email, "otp": otp})
        if user:
            users_collection.update_one(
                {"_id": user["_id"]},
                {"$set": {"is_verified": True, "otp": None}}
            )
            return True
    except Exception as e:
        logging.error(f"OTP verification error: {e}")
    return False

def get_all_users():
    if users_collection is None:
        return []
    try:
        users = users_collection.find().sort("created_at", -1)
        return [serialize_user(u) for u in users]
    except Exception as e:
        logging.error(f"Error fetching all users: {e}")
        return []

def update_user_status(user_id, is_active=None, is_admin=None):
    if users_collection is None:
        return
    updates = {}
    if is_active is not None:
        updates["is_active"] = is_active
    if is_admin is not None:
        updates["is_admin"] = is_admin
    
    if updates:
        try:
            users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": updates})
        except Exception as e:
            logging.error(f"Error updating user status: {e}")

def delete_user(user_id):
    if users_collection is None:
        return
    try:
        users_collection.delete_one({"_id": ObjectId(user_id)})
    except Exception as e:
        logging.error(f"Error deleting user: {e}")
