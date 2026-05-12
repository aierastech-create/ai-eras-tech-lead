import os
import logging
from datetime import datetime
import hashlib
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE")

if not SUPABASE_URL or not SUPABASE_KEY:
    logging.error("Supabase credentials not found in environment variables.")
    supabase = None
else:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def hash_password(password):
    """Simple SHA256 hashing for passwords."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """
    Initializes the database. 
    Note: In Supabase, you should run the SQL schema in the dashboard.
    This function will ensure the Super Admin exists.
    """
    if not supabase:
        return

    admin_email = os.getenv("ADMIN_EMAIL", "aierastech@gmail.com")
    admin_pass = os.getenv("ADMIN_PASSWORD", "Aierastech@987")
    hashed_pass = hash_password(admin_pass)

    # Check if admin exists
    try:
        response = supabase.table("ai-eras-lead-user-table").select("*").eq("email", admin_email).execute()
        if not response.data:
            # Create admin
            supabase.table("ai-eras-lead-user-table").insert({
                "username": "Admin",
                "email": admin_email,
                "password": hashed_pass,
                "is_verified": True,
                "is_active": True,
                "is_admin": True
            }).execute()
            logging.info("Super Admin created in Supabase.")
        else:
            # Update admin password just in case
            supabase.table("ai-eras-lead-user-table").update({
                "password": hashed_pass,
                "is_admin": True,
                "is_active": True
            }).eq("email", admin_email).execute()
            logging.info("Super Admin updated in Supabase.")
    except Exception as e:
        logging.error(f"Error initializing Supabase: {e}")

def register_user(username, email, phone, password, is_admin=False):
    """Registers a new user."""
    if not supabase:
        return False
    
    hashed = hash_password(password)
    try:
        response = supabase.table("ai-eras-lead-user-table").insert({
            "username": username,
            "email": email,
            "phone": phone,
            "password": hashed,
            "is_admin": is_admin
        }).execute()
        return len(response.data) > 0
    except Exception as e:
        logging.error(f"Registration error: {e}")
        return False

def get_user_by_email(email):
    if not supabase:
        return None
    try:
        response = supabase.table("ai-eras-lead-user-table").select("*").eq("email", email).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logging.error(f"Error fetching user by email: {e}")
        return None

def get_user_by_username(username):
    if not supabase:
        return None
    try:
        response = supabase.table("ai-eras-lead-user-table").select("*").eq("username", username).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        logging.error(f"Error fetching user by username: {e}")
        return None

def authenticate_user(identifier, password):
    """Authenticates by email or username."""
    if not supabase:
        return None
    
    hashed = hash_password(password)
    try:
        # Supabase doesn't support OR natively in a simple way like SQL without specialized syntax
        # We'll check email first, then username
        user = get_user_by_email(identifier)
        if not user:
            user = get_user_by_username(identifier)
            
        if user and user['password'] == hashed:
            # Update last login
            now = datetime.now().isoformat()
            supabase.table("ai-eras-lead-user-table").update({"last_login": now}).eq("id", user['id']).execute()
            return user
    except Exception as e:
        logging.error(f"Authentication error: {e}")
        
    return None

def set_user_otp(email, otp):
    if not supabase:
        return
    try:
        supabase.table("ai-eras-lead-user-table").update({"otp": otp}).eq("email", email).execute()
    except Exception as e:
        logging.error(f"Error setting OTP: {e}")

def verify_user_otp(email, otp):
    if not supabase:
        return False
    try:
        response = supabase.table("ai-eras-lead-user-table").select("*").eq("email", email).eq("otp", otp).execute()
        if response.data:
            user_id = response.data[0]['id']
            supabase.table("ai-eras-lead-user-table").update({"is_verified": True, "otp": None}).eq("id", user_id).execute()
            return True
    except Exception as e:
        logging.error(f"OTP verification error: {e}")
    return False

def get_all_users():
    if not supabase:
        return []
    try:
        response = supabase.table("ai-eras-lead-user-table").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        logging.error(f"Error fetching all users: {e}")
        return []

def update_user_status(user_id, is_active=None, is_admin=None):
    if not supabase:
        return
    updates = {}
    if is_active is not None:
        updates["is_active"] = is_active
    if is_admin is not None:
        updates["is_admin"] = is_admin
    
    if updates:
        try:
            supabase.table("ai-eras-lead-user-table").update(updates).eq("id", user_id).execute()
        except Exception as e:
            logging.error(f"Error updating user status: {e}")

def delete_user(user_id):
    if not supabase:
        return
    try:
        supabase.table("ai-eras-lead-user-table").delete().eq("id", user_id).execute()
    except Exception as e:
        logging.error(f"Error deleting user: {e}")
