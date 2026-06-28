import os
import logging
import database as db

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_database():
    logging.info("Starting MongoDB database verification...")

    # 1. Initialize DB (should create/update Super Admin)
    logging.info("Step 1: Initializing database...")
    db.init_db()
    
    # Verify Admin was created
    admin_email = os.getenv("ADMIN_EMAIL", "aierastech@gmail.com")
    admin = db.get_user_by_email(admin_email)
    if admin:
        logging.info(f"✅ Success: Found Super Admin: {admin['username']} ({admin['email']})")
        logging.info(f"Admin details: {admin}")
    else:
        logging.error("❌ Failure: Super Admin was not found in the database.")
        return False

    # 2. Register a new user
    test_username = "test_user_123"
    test_email = "test_user_123@example.com"
    test_phone = "1234567890"
    test_password = "password123"
    
    logging.info(f"Step 2: Registering test user '{test_username}'...")
    # Clean up existing test user if any
    existing = db.get_user_by_email(test_email)
    if existing:
        logging.info("Test user already exists, deleting first...")
        db.delete_user(existing['id'])

    registered = db.register_user(test_username, test_email, test_phone, test_password)
    if registered:
        logging.info("✅ Success: Test user registered successfully.")
    else:
        logging.error("❌ Failure: Failed to register test user.")
        return False

    # 3. Fetch user
    user = db.get_user_by_email(test_email)
    if user:
        logging.info(f"✅ Success: Fetched registered user by email: {user}")
    else:
        logging.error("❌ Failure: Could not fetch user by email.")
        return False

    # 4. Authenticate user
    logging.info("Step 4: Authenticating test user...")
    authenticated_user = db.authenticate_user(test_email, test_password)
    if authenticated_user:
        logging.info(f"✅ Success: User authenticated successfully: {authenticated_user}")
    else:
        logging.error("❌ Failure: Authentication failed.")
        return False

    # 5. Set & Verify OTP
    logging.info("Step 5: Testing OTP flow...")
    db.set_user_otp(test_email, "123456")
    verified = db.verify_user_otp(test_email, "123456")
    if verified:
        logging.info("✅ Success: OTP set and verified successfully.")
        # Check if is_verified is True
        updated_user = db.get_user_by_email(test_email)
        if updated_user and updated_user.get("is_verified"):
            logging.info("✅ Success: User is now marked as verified.")
        else:
            logging.error("❌ Failure: User was verified but is_verified field is not True.")
            return False
    else:
        logging.error("❌ Failure: OTP verification failed.")
        return False

    # 6. Update user status
    logging.info("Step 6: Updating user status...")
    db.update_user_status(user['id'], is_active=True, is_admin=True)
    updated_user = db.get_user_by_email(test_email)
    if updated_user and updated_user.get("is_active") and updated_user.get("is_admin"):
        logging.info("✅ Success: User status and role updated successfully.")
    else:
        logging.error("❌ Failure: Failed to update user status/role.")
        return False

    # 7. Get all users
    logging.info("Step 7: Fetching all users...")
    all_users = db.get_all_users()
    if all_users:
        logging.info(f"✅ Success: Fetched {len(all_users)} user(s).")
    else:
        logging.error("❌ Failure: Failed to fetch all users.")
        return False

    # 8. Delete user
    logging.info(f"Step 8: Deleting test user...")
    db.delete_user(user['id'])
    deleted_user = db.get_user_by_email(test_email)
    if not deleted_user:
        logging.info("✅ Success: Test user deleted successfully.")
    else:
        logging.error("❌ Failure: Test user was not deleted.")
        return False

    logging.info("🎉 All database operations verified successfully on MongoDB!")
    return True

if __name__ == "__main__":
    test_database()
