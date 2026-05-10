import sqlite3
import logging
from datetime import datetime
import hashlib
import os

DB_NAME = "users.db"

def get_connection():
    return sqlite3.connect(DB_NAME)

def hash_password(password):
    """Simple SHA256 hashing for passwords."""
    return hashlib.sha256(password.encode()).hexdigest()

def init_db():
    """Initializes the database and resets it if the old schema is detected."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if the 'username' column exists to detect old schema
    cursor.execute("PRAGMA table_info(users)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if columns and "username" not in columns:
        logging.info("Old database schema detected. Resetting database...")
        cursor.execute("DROP TABLE users")
    
    # Create new table with updated fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            email TEXT UNIQUE,
            phone TEXT,
            password TEXT,
            otp TEXT,
            is_verified BOOLEAN DEFAULT 0,
            is_active BOOLEAN DEFAULT 0,
            is_admin BOOLEAN DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME
        )
    ''')
    conn.commit()
    
    # Ensure Super Admin exists
    admin_email = os.getenv("ADMIN_EMAIL", "aierastech@gmail.com")
    admin_pass = os.getenv("ADMIN_PASSWORD", "Aierastech@987")
    hashed_pass = hash_password(admin_pass)
    
    cursor.execute('''
        INSERT INTO users (username, email, password, is_verified, is_active, is_admin)
        VALUES (?, ?, ?, 1, 1, 1)
        ON CONFLICT(email) DO UPDATE SET
            password = excluded.password,
            is_admin = 1,
            is_active = 1
    ''', ("Admin", admin_email, hashed_pass))
    
    conn.commit()
    conn.close()
    logging.info("Custom Auth Database initialized with Super Admin.")

def register_user(username, email, phone, password, is_admin=0):
    """Registers a new user (initially unverified and inactive)."""
    conn = get_connection()
    cursor = conn.cursor()
    hashed = hash_password(password)
    
    try:
        cursor.execute('''
            INSERT INTO users (username, email, phone, password, is_admin)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, email, phone, hashed, is_admin))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False
    
    conn.close()
    return success

def get_user_by_email(email):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_by_username(username):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def authenticate_user(identifier, password):
    """Authenticates by email or username."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    hashed = hash_password(password)
    
    cursor.execute('''
        SELECT * FROM users 
        WHERE (email = ? OR username = ?) AND password = ?
    ''', (identifier, identifier, hashed))
    
    user = cursor.fetchone()
    if user:
        # Update last login
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user['id']))
        conn.commit()
        
    conn.close()
    return dict(user) if user else None

def set_user_otp(email, otp):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET otp = ? WHERE email = ?", (otp, email))
    conn.commit()
    conn.close()

def verify_user_otp(email, otp):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE email = ? AND otp = ?", (email, otp))
    user = cursor.fetchone()
    if user:
        cursor.execute("UPDATE users SET is_verified = 1, otp = NULL WHERE id = ?", (user[0],))
        conn.commit()
        conn.close()
        return True
    conn.close()
    return False

def get_all_users():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    conn.close()
    return [dict(u) for u in users]

def update_user_status(user_id, is_active=None, is_admin=None):
    conn = get_connection()
    cursor = conn.cursor()
    if is_active is not None:
        cursor.execute("UPDATE users SET is_active = ? WHERE id = ?", (1 if is_active else 0, user_id))
    if is_admin is not None:
        cursor.execute("UPDATE users SET is_admin = ? WHERE id = ?", (1 if is_admin else 0, user_id))
    conn.commit()
    conn.close()

def delete_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
