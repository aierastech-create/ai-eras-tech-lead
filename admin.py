import streamlit as st
import pandas as pd
import database as db
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    st.set_page_config(page_title="Admin Control Center", page_icon="🛡️", layout="wide")
    db.init_db()
    
    admin_email = os.getenv("ADMIN_EMAIL", "aierastech@gmail.com")
    admin_password = os.getenv("ADMIN_PASSWORD", "Aierastech@987")

    if 'admin_logged_in' not in st.session_state:
        st.session_state['admin_logged_in'] = False

    if not st.session_state['admin_logged_in']:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.title("🛡️ Admin Login")
            email = st.text_input("Admin Email")
            password = st.text_input("Password", type="password")
            if st.button("Login", type="primary", use_container_width=True):
                if email == admin_email and password == admin_password:
                    st.session_state['admin_logged_in'] = True
                    st.rerun()
                else:
                    st.error("Invalid Admin Credentials")
        return

    # --- Authenticated Admin UI ---
    st.title("🛡️ Admin Control Center")
    st.markdown("Manage users, monitor sign-ups, and control application access.")

    with st.sidebar:
        st.markdown(f"### Logged in as Admin")
        st.caption(admin_email)
        st.divider()
        if st.sidebar.button("Logout", use_container_width=True):
            st.session_state['admin_logged_in'] = False
            st.rerun()

    users = db.get_all_users()
    if not users:
        st.info("No users found.")
    else:
        # Filter out the super admin from the management list
        other_users = [u for u in users if u['email'] != admin_email]
        
        st.divider()
        st.subheader("👥 User Management Directory")
        
        if not other_users:
            st.info("No users have signed up yet.")
        else:
            # Header Row
            h1, h2, h3, h4, h5 = st.columns([2, 3, 2, 2, 2])
            h1.markdown("**Username**")
            h2.markdown("**Email**")
            h3.markdown("**Phone**")
            h4.markdown("**Verified**")
            h5.markdown("**Access Control**")
            st.divider()

            for u in other_users:
                c1, c2, c3, c4, c5 = st.columns([2, 3, 2, 2, 2])
                c1.write(u['username'])
                c2.write(u['email'])
                c3.write(u['phone'])
                c4.write("✅ Verified" if u['is_verified'] else "❌ Unverified")
                
                with c5:
                    is_active = st.toggle("Allow", value=bool(u['is_active']), key=f"act_{u['id']}")
                    if is_active != bool(u['is_active']):
                        db.update_user_status(u['id'], is_active=is_active)
                        st.rerun()
                
                # Small delete button in a separate row to keep it clean
                with st.expander(f"More options for {u['username']}"):
                    col_del, col_role = st.columns(2)
                    with col_del:
                        if st.button("🗑️ Delete Account", key=f"del_{u['id']}", type="secondary"):
                            db.delete_user(u['id'])
                            st.rerun()
                    with col_role:
                        is_adm = st.checkbox("Make Admin", value=bool(u['is_admin']), key=f"adm_{u['id']}")
                        if is_adm != bool(u['is_admin']):
                            db.update_user_status(u['id'], is_admin=is_adm)
                            st.rerun()
                st.divider()

if __name__ == "__main__":
    main()
